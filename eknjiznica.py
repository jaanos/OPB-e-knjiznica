#uvoz Bottla
from re import TEMPLATE
from bottleext import *

#uvoz podatkov za povezavo
import auth_public as auth

#Uvoz psycopg2
import psycopg2, psycopg2.extensions, psycopg2.extras 
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

import hashlib

from datetime import date


# KONFIGURACIJA

#Privzete nastavitve
SERVER_PORT = os.environ.get('BOTTLE_PORT', 8080)
RELOADER = os.environ.get('BOTTLE_RELOADER', True)
ROOT = os.environ.get('BOTTLE_ROOT', '/')
DB_PORT = os.environ.get('POSTGRES_PORT', 5432)

# Odkomentiraj, če želiš sporočila o napakah
debug(True)  # za izpise v terminalu, pomaga pri iskanju


#___________________________________________________________________________________________________________________________
#FUNKCIJE
def rtemplate(*largs, **kwargs):
    """
    Izpis predloge s podajanjem spremenljivke ROOT z osnovnim URL-jem.
    """
    return template(ROOT=ROOT, *largs, **kwargs)


#___________________________________________________________________________________________________________________________
#ZAČETNA STRAN
@get('/')
def index():
    redirect(url('prijava_get'))

def nastaviSporocilo(sporocilo = None):
    staro = request.get_cookie("sporocilo", secret=skrivnost)
    if sporocilo is None:
        response.delete_cookie('sporocilo')
    else:
        response.set_cookie('sporocilo', sporocilo, path="/", secret=skrivnost)
    return staro 


def preveriUporabnika(): 
    username = request.get_cookie("username", secret=skrivnost)
    if username:
        cur = baza.cursor()    
        oseba = None
        try: 
            cur.execute("SELECT * FROM uporabnik WHERE username = %s", (username, ))
            oseba = cur.fetchone()
            print(oseba)  #v oseba se shranijo vsi podatki o uporabniku
        except:
            oseba = None
        if oseba: 
            return oseba
    redirect(url('prijava_get'))

def hashGesla(s):
    m = hashlib.sha256()
    m.update(s.encode("utf-8"))
    return m.hexdigest()

# Mapa za statične vire (slike, css, ...)
static_dir = "./static"

skrivnost = "rODX3ulHw3ZYRdbIVcp1IfJTDn8iQTH6TFaNBgrSkjIulr"

@route("/static/<filename:path>")
def static(filename):
    return static_file(filename, root=static_dir)


#___________________________________________________________________________________________________________________________
#PRIJAVA
@get('/prijava')
def prijava_get():
    napaka = nastaviSporocilo()
    return template('prijava.html', napaka=napaka)

@post('/prijava')
def prijava_post():
    username = request.forms.username
    geslo = request.forms.password
    if username is None or geslo is None:
        nastaviSporocilo('Uporabniško ime in geslo morata biti neprazna') 
        redirect(url('prijava_get'))
    cur = baza.cursor()    
    hashBaza = None
    try: 
        cur.execute("SELECT geslo FROM uporabnik WHERE username = %s", (username, ))
        hashBaza, = cur.fetchone()
        print(hashBaza)
        print(geslo)
    except Exception as x:
        hashBaza = None
        print(x)
    if hashBaza is None:
        nastaviSporocilo('Uporabniško ime ali geslo nista ustrezni') 
        redirect(url('prijava_get'))
        return
    if geslo != hashBaza:
        nastaviSporocilo('Uporabniško ime ali geslo nista ustrezni') 
        redirect(url('prijava_get'))
        return
    response.set_cookie('username', username, secret=skrivnost)
    redirect(url('uporabnik'))


#___________________________________________________________________________________________________________________________
#ODJAVA
@get('/odjava')
def odjava_get():
    response.delete_cookie('username')
    redirect(url('prijava_get'))


#___________________________________________________________________________________________________________________________
#UPORABNIK

@get('/uporabnik')
def uporabnik():
    oseba = preveriUporabnika()
    if oseba is None: 
        return
    napaka = nastaviSporocilo()
    cur.execute("""SELECT COUNT (*) FROM transakcija WHERE id_uporabnika=%s""", (oseba[1], ))
    st_knjig = cur.fetchone()
    st_knjig = st_knjig[0]
    krediti = 0
    sporocilo = ''
    if oseba[6]=='basic': 
        krediti = 5 - st_knjig
        if krediti <= 0:
            sporocilo='Število razpoložljivih kreditov je 0.'
    else:   
        krediti = 10 - st_knjig
        if krediti < 0:
            sporocilo='Število razpoložljivih kreditov je 0.'
    return template('uporabnik.html', oseba=oseba, napaka=napaka, krediti = krediti, sporocilo=sporocilo)


def preveri_za_uporabnika(username, email):
    try:
        cur.execute("SELECT username, email FROM uporabnik WHERE username, email = %s, %s", (username, email))
        uporabnik = cur.fetchone()
        if uporabnik==None:
            return True
        else:
            return False
    except:
        return False
    
#___________________________________________________________________________________________________________________________
# REGISTRACIJA
@get('/registracija')
def registracija_get():
    napaka = nastaviSporocilo()
    return template('registracija.html', napaka=napaka)

@post('/registracija')
def registracija_post():
    username = request.forms.username
    ime = request.forms.ime
    priimek = request.forms.priimek
    email = request.forms.email
    password = request.forms.password
    password2 = request.forms.password2
    subscription = request.forms.subscription

    #preverimo, ce je izbrani username ze zaseden
    cur = baza.cursor()
    cur.execute("SELECT * FROM uporabnik WHERE username=%s", (username,))
    upor = cur.fetchone()
    if upor is not None:
        return template("registracija.html", ime=ime, priimek=priimek, username=username,
                               email=email, napaka="Uporabniško ime je že zasedeno!")

    # preverimo, ali se gesli ujemata
    if password != password2:
        return template("registracija.html", ime=ime, priimek=priimek, username=username,
                               email=email, napaka="Gesli se ne ujemata!")

    #preverimo, ali ima geslo vsaj 4 znake
    if len(password) < 4:
        return template("registracija.html", ime=ime, priimek=priimek, username=username,
                               email=email, napaka="Geslo mora imeti vsaj 4 znake!")
    

    #ce pridemo, do sem, je vse uredu in lahko vnesemo zahtevek v bazo
    zgostitev = hashGesla(password)
    cur.execute("UPDATE uporabnik SET geslo = %s WHERE username = %s", (zgostitev, username))
    response.set_cookie('username', username, secret=skrivnost)
    cur.execute("INSERT INTO uporabnik (ime, priimek, username, geslo, email, narocnina) VALUES (%s, %s, %s, %s, %s, %s)", (ime, priimek, username, password, email, subscription))
    baza.commit()
    redirect(url('uporabnik'))

#___________________________________________________________________________________________________________________________
# KNJIŽNICA
@get('/knjiznica')
def knjiznica_get():
    napaka = nastaviSporocilo()
    cur = baza.cursor()
    knjige = cur.execute("""
        SELECT id_knjige, naslov, avtor.ime, cena_nakupa FROM knjige
        INNER JOIN avtor ON avtor.id_avtorja = knjige.id_avtorja
    """)
    knjige = cur.fetchall()
    return template('knjiznica.html', napaka=napaka, knjige = knjige)


@post('/knjiznica/kupi/<id_knjige>')
def kupi_knjigo(id_knjige):
    oseba = preveriUporabnika()
    id_uporabnika = oseba[1]
    today = date.today()
    d1 = today.strftime("%d/%m/%Y")
    cur = baza.cursor()
    kupljeno = cur.execute("SELECT * FROM transakcija WHERE id_knjige=%s AND id_uporabnika=%s", (id_knjige, id_uporabnika, ))
    kupljeno = cur.fetchall()
    if kupljeno!=[]:
        nastaviSporocilo('To knjigo že imate v svoji knjižnici!')
        redirect(url('moja_knjiznica_get'))
    else:
        cur.execute("""SELECT COUNT (*) FROM transakcija WHERE id_uporabnika=%s""", (oseba[1], ))
        st_knjig = cur.fetchone()
        st_knjig = st_knjig[0]
        krediti = 0
        if oseba[6]=='basic': 
            krediti = 5 - st_knjig
            if krediti <= 0:
                nastaviSporocilo('Prekoračili ste dovoljeno število izposojenih knjig!')
                redirect(url('moja_knjiznica_get'))
            else:
                cur.execute("INSERT INTO transakcija (id_uporabnika, id_knjige, tip, datum) VALUES (%s, %s, 'nakup', %s)", (id_uporabnika, id_knjige, d1))
                baza.commit()
                nastaviSporocilo('Izposoja je uspela!')
                redirect(url('moja_knjiznica_get'))
        else:  
            krediti = 10 - st_knjig
            if krediti <= 0:
                nastaviSporocilo('Vaša eKnjižnica je polna, pred izposojo nove morate vrniti eno izmed knjig.')
                redirect(url('moja_knjiznica_get'))
            else:
                cur.execute("INSERT INTO transakcija (id_uporabnika, id_knjige, tip, datum) VALUES (%s, %s, 'nakup', %s)", (id_uporabnika, id_knjige, d1))
                nastaviSporocilo('Izposoja je uspela!')
                baza.commit()
                redirect(url('moja_knjiznica_get'))


#___________________________________________________________________________________________________________________________
# UPORABNIKOVA IZBIRKA KNJIG
@get('/moje_knjige')
def moja_knjiznica_get():
    napaka = nastaviSporocilo()
    oseba = preveriUporabnika()
    id_uporabnika = oseba[1]
    cur = baza.cursor()
    k = cur.execute("""SELECT knjige.id_knjige, knjige.naslov, avtor.ime, datum FROM transakcija 
                        INNER JOIN knjige ON transakcija.id_knjige = knjige.id_knjige
                        INNER JOIN avtor ON knjige.id_avtorja = avtor.id_avtorja
                        WHERE id_uporabnika=%s""",(id_uporabnika,))
    k = cur.fetchall()
    st_knjig = cur.execute("""SELECT COUNT (*) FROM transakcija WHERE id_uporabnika=%s""", (oseba[1], ))
    st_knjig = cur.fetchone()
    st_knjig = st_knjig[0]
    krediti = 0
    if oseba[6]=='basic': 
        krediti = 5 - st_knjig
    else:
        krediti = 10 - st_knjig
    return template('moje_knjige.html', napaka=napaka, knjige=k, krediti = krediti)

@post('/knjiznica/vrni/<id_knjige>')
def vrni_knjigo(id_knjige):
    oseba = preveriUporabnika()
    id_uporabnika = oseba[1]
    cur = baza.cursor()
    cur.execute("""DELETE FROM transakcija WHERE id_knjige=%s AND id_uporabnika=%s""", (id_knjige, id_uporabnika, ))
    nastaviSporocilo('Knjigo ste uspešno vrnili. Vstopite v eKnjižnico za izposojo nove.')
    baza.commit()
    redirect(url('moja_knjiznica_get'))


#___________________________________________________________________________________________________________________________
#POVEZAVA NA BAZO
baza = psycopg2.connect(database=auth.dbname, host=auth.host, user=auth.user, password=auth.password, port = DB_PORT)
# baza.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cur = baza.cursor(cursor_factory=psycopg2.extras.DictCursor)

#Požnemo strežnik na podanih vratih
run(host='localhost', port=SERVER_PORT, reloader=RELOADER) # reloader=True nam olajša razvoj (ozveževanje sproti - razvoj)
