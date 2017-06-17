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
db = postgresql.open("pq://tharyrok:tharyrok@127.0.0.1/ispng")

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
#  Clean user is bdd and not ldap
#

result = db.prepare('SELECT ovpn_clients."userId" FROM public.ovpn_clients')

for i in result:
    res = l.search_s("ou=Users,dc=neutrinet,dc=be", ldap.SCOPE_SUBTREE, "(uid=" + str(i["userId"]) + ")")
    if len(res) < 1:
        db.execute('DELETE FROM ovpn_clients WHERE "userId" = \'%s\';' % str(i["userId"]))

#
# clean serial is bbd and not server
#

results = db.prepare('SELECT certificates.serial, certificates.id FROM public.certificates')

for result in results:
    if not any(d.get('serial', None) == str(result['serial']) for d in certificates):
        db.execute('DELETE FROM certificates WHERE id = %d;' % result["id"])

#
# clean certificate not associate ip
#

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
            os.remove(cert.file)
        except FileNotFoundError:
            pass

#
# Liberate ip is not associate member
#

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

#
# Liberate ip is not associate certificate
#
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

#
# Clean old certificate for member if one certificate valid
#

member_list_serial = {}

results = db.prepare('SELECT '
                        'certificates.serial, '
                        'certificates.client_id '
                     'FROM '
                        'public.certificates,'
                        'public.ovpn_clients '
                     'WHERE '
                        'certificates.client_id = ovpn_clients.id')

# restructure result
for i in results:
    if i['client_id'] in member_list_serial:
        member_list_serial[i['client_id']].append(i['serial'])
    else:
        member_list_serial[i['client_id']] = []
        member_list_serial[i['client_id']].append(i['serial'])

for client, certs_for_member in member_list_serial.items():
    if len(certs_for_member) > 1:
        for cert_for_member in certs_for_member:
            # find certificate not expire
            try:
                end_date = [element for element in certificates if element['serial'] == cert_for_member][0]
            except IndexError:
                break
            if end_date['end_date'] >= datetime.datetime.now():
                # delete other certificate
                db.execute(
                    'DELETE FROM certificates WHERE client_id=%d AND NOT serial=\'%s\';' % (client, cert_for_member))
                for cert_old_for_member in certs_for_member:
                    if cert_old_for_member is not cert_for_member:
                        try:
                            try:
                                os.remove(
                                    [element for element in certificates if element['serial'] == cert_old_for_member][
                                        0]['file'])
                            except IndexError:
                                pass
                        except FileNotFoundError:
                            pass

#
# Find member for certificate expire to 90 days and expire for 180 days
#

member_list_serial = {}

results = db.prepare('SELECT '
                        'certificates.serial, '
                        'ovpn_clients."userId" '
                     'FROM '
                        'public.certificates,'
                        'public.ovpn_clients '
                     'WHERE '
                        'certificates.client_id = ovpn_clients.id')

# restructure result
for i in results:
    if i['userId'] in member_list_serial:
        member_list_serial[i['userId']].append(i['serial'])
    else:
        member_list_serial[i['userId']] = []
        member_list_serial[i['userId']].append(i['serial'])

for user_id, serials in member_list_serial.items():
    end_180 = False
    end_90 = False
    valid = False

    for serial in serials:
        try:
            end_date = [element for element in certificates if element['serial'] == serial][0]['end_date']
        except IndexError:
            break

        if end_date <= (datetime.datetime.now() - datetime.timedelta(days=180)):
            end_180 = end_date

        elif end_date <= datetime.datetime.now():
            end_180 = end_date

        elif end_date <= (datetime.datetime.now() + datetime.timedelta(days=90)):
            end_90 = end_date

        else:
            valid = end_date

    res = l.search_s(
        "ou=Users,dc=neutrinet,dc=be",
        ldap.SCOPE_SUBTREE,
        "(uid=" + str(user_id) + ")",
    )

    if res:
        if end_180 and not (end_90 or valid):
            print('L\'user %s à un certificat qui à expiré %s' % (
            res[0][1]['mail'][0].decode("utf-8"), (datetime.datetime.now() - end_180)))

        if end_90 and not valid:
            print('L\'user %s à un certificat qui va expiré %s' % (
            res[0][1]['mail'][0].decode("utf-8"), (end_90 - datetime.datetime.now())))

        if valid:
            print('L\'user %s n\'à pas un certificat qui va expiré %s' % (res[0][1]['mail'][0].decode("utf-8"), valid))

l.unbind()
