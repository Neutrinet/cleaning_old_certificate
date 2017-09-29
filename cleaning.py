import ldap
import pprint
import postgresql
import glob
import os

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

import datetime

#
#  Connexion LDAP
#

l = ldap.initialize("ldap://localhost:8389")
login_dn = "cn=admin,dc=neutrinet,dc=be"
login_pw = "password"
l.simple_bind_s(login_dn, login_pw)

#
#  Connexion SQL
#
db = postgresql.open("pq://tharyrok:tharyrok@127.0.0.1/ispng_beta")

#
#  Cache certificate
#

certificates = []

for i in glob.glob('/home/tharyrok/developpement/neutrinet/cert/*.crt'):
    cert = x509.load_pem_x509_certificate(open(i, "rb").read(), default_backend())
    certificates.append({
        'serial': str(cert.serial_number),
        'end_date': cert.not_valid_after,
        'file': i
    })

#
#  Clean users who are present in the db but not in ldap
#
print('Cleaning users who are present in the db but not in ldap')

result = db.prepare('SELECT ovpn_clients."userId" FROM public.ovpn_clients')

for i in result:
    res = l.search_s("ou=Users,dc=neutrinet,dc=be", ldap.SCOPE_SUBTREE, "(uid=" + str(i["userId"]) + ")")
    if len(res) < 1:
        db.execute('DELETE FROM ovpn_clients WHERE "userId" = \'%s\';' % str(i["userId"]))
        print('Removing %s from database, as \(s\)he was absent from LDAP)', str(i["userId"]))

#
# clean serial is bbd and not server
#
print('Cleaning serials from DB that are not found on the server\'s filesystem as well')


results = db.prepare('SELECT certificates.serial, certificates.id FROM public.certificates')

for result in results:
    i = next((item for item in certificates if item.get("serial") and item["serial"] == result['serial']), None)
    if not i:
        db.execute('DELETE FROM certificates WHERE id = %d;' % result["id"])
        print('Removing %s\'s certificate from the DB, as its serial is not present on the server\'s file system', str(result["id"]))

#
# clean certificate not associate ip
#
print('Cleaning certificates that are not associated with an ip')


for cert in certificates:
    result = db.prepare(
        'SELECT '
            'count(*) '
        'FROM '
            'public.certificates, public.address_pool '
        'WHERE '
            'address_pool.client_id = certificates.client_id AND '
            'certificates.serial=\'%s\';' % cert['serial']).first()

    if result is 0:
        try:
            os.remove(cert['file'])
            print('Removing %s from the file system, as it is not associated with any ip', str(cert['file']))

        except FileNotFoundError:
            pass

#
# Liberate ip is not associate member
#
print('Liberating IPv4 adresses that are not associated with any existing member')

results = db.prepare(
    'SELECT '
        'id '
    'FROM '
        'address_pool '
    'WHERE '
        '"ipVersion"=4 AND '
        'client_id NOT IN (SELECT id FROM ovpn_clients) AND '
        'NOT client_id=-1;')

for i in results:
    db.execute('UPDATE address_pool SET client_id = -1 WHERE id = %s' % i["id"])
    print('Removing address %s as it is not associated with any member existing in DB', str(i["id"]))

#
# Liberate ip is not associate certificate
#
print('Liberating IP addresses that are not associated with any certificate')

result = db.prepare(
    'SELECT '
       'id '
    'FROM '
        'address_pool '
    'WHERE '
        '"ipVersion"=4 AND '
        'client_id NOT IN (SELECT client_id FROM certificates) AND '
        'NOT client_id=-1;')

for i in result:
    db.execute('UPDATE address_pool SET client_id = -1 WHERE id = %s' % i["id"])
    print('Removing address with id %s as it had no corresponding certificate in DB', str(i["id"]))

#
# Clean old certificate for member if one certificate valid
#
print('Cleaning expired certificates when the member still has at least one valid certificate')

member_list_serial = {}
results = db.prepare('SELECT '
                        'certificates.serial, '
                        'certificates.client_id, '
                        'ovpn_clients."userId" '
                     'FROM '
                        'public.certificates,'
                        'public.ovpn_clients '
                     'WHERE '
                        'certificates.client_id = ovpn_clients.id ')


# Remove certificate not in the server
for result in results:
    cert = next((item for item in certificates if item.get("serial") and item["serial"] == result['serial']), None)
    if not cert:
        # delete other certificate
        db.execute(
            'DELETE FROM certificates WHERE serial=\'%s\';' % (str(result['serial'])))
        print('Remove %s', str(result['serial']))
    else:
        cert['user_id'] = result['userId']

        if result['client_id'] in member_list_serial:
            member_list_serial[result['client_id']].append(cert)
        else:
            member_list_serial[result['client_id']] = []
            member_list_serial[result['client_id']].append(cert)

# Remove multiples certificates
for members in member_list_serial:
    if len(member_list_serial[members]) > 1:
        last = datetime.datetime.fromtimestamp(1)
        last_elem = None
        for member in member_list_serial[members]:
            if last < member['end_date']:
                if last_elem:
                    member_list_serial[members].remove(last_elem)
                last = member['end_date']
                last_elem = member
            else:
                # delete other certificate
                db.execute('DELETE FROM certificates WHERE serial=\'%s\';' % (str(member['serial'])))
                try:
                    os.remove(member['file'])
                except FileNotFoundError:
                    pass
                print('Remove %s', str(member['serial']))
                member_list_serial[members].remove(member)

for user_id, serials in member_list_serial.items():
    end_180 = False
    end_90 = False
    valid = False

    serial_end_180 = False
    serial_end_90 = False
    serial_valid = False

    serial = serials[0]['serial']
    end_date = serials[0]['end_date']
    user_id = serials[0]['user_id']

    if end_date <= (datetime.datetime.now() - datetime.timedelta(days=180)):
        end_180 = end_date
        serial_end_180 = serial

    elif end_date <= datetime.datetime.now():
        end_180 = end_date
        serial_end_180 = serial

    elif end_date <= (datetime.datetime.now() + datetime.timedelta(days=90)):
        end_90 = end_date
        serial_end_90 = serial

    else:
        valid = end_date
        serial_valid = serial

    res = l.search_s(
        "ou=Users,dc=neutrinet,dc=be",
        ldap.SCOPE_SUBTREE,
        "(uid=" + str(user_id) + ")",
    )

    if res:
        if end_180 and not (end_90 or valid):
            print('L\'utilisateur %s a un certificat qui a expiré %s :: %s' % (
            res[0][1]['mail'][0].decode("utf-8"), (datetime.datetime.now() - end_180), serial_end_180))

        if end_90 and not valid:
            print('L\'utilisateur %s a un certificat qui va expirer %s :: %s' % (
            res[0][1]['mail'][0].decode("utf-8"), (end_90 - datetime.datetime.now()), serial_end_90))

        if valid:
            print('L\'utilisateur %s n\'a pas de certificat qui va expirer %s :: %s' % (res[0][1]['mail'][0].decode("utf-8"), valid, serial_valid))


l.unbind()
