import ldap
import pprint
import postgresql
import glob
import os

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

import datetime

### Connexion LDAP
l = ldap.initialize("127.0.0.1")
login_dn = "cn=admin,dc=neutrinet,dc=be"
login_pw = "password"
l.simple_bind_s(login_dn, login_pw)

### Connexion SQL
db = postgresql.open("pq://ispng:ispng@127.0.0.1/ispng")

### On netoye les users qui sont dans la bdd mais pas dans ldap
result = db.prepare('SELECT ovpn_clients."userId" FROM public.ovpn_clients')

for i in result:
    res = l.search_s("ou=Users,dc=neutrinet,dc=be", ldap.SCOPE_SUBTREE, "(uid=" + str(i["userId"]) + ")")
    if len(res) != 1:
        db.execute("DELETE FROM ovpn_clients WHERE 'userId' = '%s';" % str(i["userId"]))

### On netoye les certificat qui sont dans la bdd mais pas sur le serveur
serials = []

for i in glob.glob('/opt/ispng/ca/store/*.crt'):
    cert = x509.load_pem_x509_certificate(open(i, "rb").read(), default_backend())
    serials.append(str(cert.serial_number))

results = db.prepare('SELECT certificates.serial, certificates.id FROM public.certificates')

for result in results:
    if not str(result['serial']) in serials:
        db.execute('DELETE FROM certificates WHERE id = %d;' % result["id"])

### On supprime les certificats qui sont lier à aucune ip
for i in glob.glob('/opt/ispng/ca/store/*.crt'):
    cert = x509.load_pem_x509_certificate(open(i, "rb").read(), default_backend())
    results = db.prepare(
        'SELECT count(*) FROM public.certificates, public.address_pool WHERE address_pool.client_id = certificates.client_id AND certificates.serial=\'%s\';' % cert.serial_number)
    for result in results:
        if result[0] is 0:
            try:
                os.remove(i)
            except FileNotFoundError:
                pass

### On libere les ip qui n'ont pas de user ni de certificat
result = db.prepare(
    'SELECT id FROM address_pool WHERE "ipVersion"=4 AND client_id NOT IN (SELECT id FROM ovpn_clients) AND NOT client_id=-1;')

for i in result:
    db.execute('UPDATE address_pool SET client_id = -1 WHERE id = %s' % i["id"])

result = db.prepare(
    'SELECT id FROM address_pool WHERE "ipVersion"=4 AND client_id NOT IN (SELECT client_id FROM certificates) AND NOT client_id=-1;')

for i in result:
    db.execute('UPDATE address_pool SET client_id = -1 WHERE id = %s' % i["id"])

### On supprime les anciens certificat qui sont lier à un membre avec un certificat valide

serials_not_expire = []

# On liste les serial qui ne sont pas expiré
for i in glob.glob('/opt/ispng/ca/store/*.crt'):
    cert = x509.load_pem_x509_certificate(open(i, "rb").read(), default_backend())
    # on trouve les certificats non expirer
    if cert.not_valid_after >= datetime.datetime.now():
        if not str(cert.serial_number) in serials_not_expire:
            serials_not_expire.append(str(cert.serial_number))

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

### On trouve les membres avec un certificat qui va expiré dans 3 mois

serials_expire_3 = []
users_id_expire = []
users_cert_date = {}

# On liste les serial qui vont expiré dans 3 mois
for i in glob.glob('/opt/ispng/ca/store/*.crt'):
    cert = x509.load_pem_x509_certificate(open(i, "rb").read(), default_backend())
    # on trouve les certificats expirer
    if cert.not_valid_after <= (datetime.datetime.now() + datetime.timedelta(days=180)):
        # on trouve l'id du client
        results = db.prepare(
            'SELECT ovpn_clients."userId" FROM public.certificates, public.ovpn_clients WHERE certificates.client_id = ovpn_clients.id AND certificates.serial=\'%s\';' % cert.serial_number).first()
        if results:
            if not result in users_id_expire:
                users_id_expire.append(results)
                users_cert_date[results] = cert.not_valid_after
            else:
                if users_cert_date[results] <= cert.not_valid_after:
                    users_cert_date[results] = cert.not_valid_after

for k, v in users_cert_date.items():
    res = l.search_s(
        "ou=Users,dc=neutrinet,dc=be",
        ldap.SCOPE_SUBTREE,
        "(uid=" + str(k) + ")",
    )
    if res:
        results = db.prepare(
            'SELECT address_pool.address FROM public.address_pool, public.ovpn_clients WHERE address_pool.client_id = ovpn_clients.id AND address_pool."ipVersion" = 4 AND ovpn_clients."userId"=\'%s\';' % k).first()
        results2 = db.prepare(
            'SELECT address_pool.address FROM public.address_pool, public.ovpn_clients WHERE address_pool.client_id = ovpn_clients.id AND address_pool."ipVersion" = 6 AND ovpn_clients."userId"=\'%s\';' % k).first()
        print(str(v) + " :: " + str(res[0][1]['mail'][0].decode("utf-8")) + " " + str(
            res[0][1]['givenName'][0].decode("utf-8")) + " " + str(
            res[0][1]['sn'][0].decode("utf-8")) + " | IP4 : " + str(results) + " IP6 : " + str(
            results2) + " userId => " + k)

pprint.pprint(serials_expire_3)
pprint.pprint(users_id_expire)
pprint.pprint(users_cert_date)

# Remove crt plus vieux de 6 mois
for i in glob.glob('/opt/ispng/ca/store/*.crt'):
    cert = x509.load_pem_x509_certificate(open(i, "rb").read(), default_backend())
    # on trouve les certificats expirer
    if cert.not_valid_after <= (datetime.datetime.now() - datetime.timedelta(days=545)):
        print(str(cert.not_valid_after) + " -> " + str(i))

l.unbind()
