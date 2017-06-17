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
    if len(res) != 1:
        db.execute("DELETE FROM ovpn_clients WHERE 'userId' = '%s';" % str(i["userId"]))



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
            'certificates.serial=\'%s\';' % cert['serial']
    ).first()
    if result is 0:
        try:
            #os.remove(cert.file)
            print(cert['file'])
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

serials_not_expire = []
serial_expire = []
all_serial_members = {}

for i in glob.glob('/opt/ispng/ca/store/*.crt'):
    cert = x509.load_pem_x509_certificate(open(i, "rb").read(), default_backend())
    # on trouve les certificats expirer
    if cert.not_valid_after <= datetime.datetime.now():
        # On recupere tout les seriel du membre
        results = db.prepare(
            'SELECT serial FROM certificates WHERE client_id=(SELECT client_id FROM certificates WHERE certificates.serial=\'%s\');' % cert.serial_number)
        for result in results:
            if str(result['serial']) in serials_not_expire:
                # le membre a au moins un certificat valid
                # On supprime le ficher et l'entrée dans la bdd
                db.execute('DELETE FROM certificates WHERE id = %d;' % cert.serial_number)
                try:
                    os.remove(i)
                except FileNotFoundError:
                    pass
l.unbind()

