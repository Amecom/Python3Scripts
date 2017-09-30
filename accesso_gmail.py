# PER POTET ACCEDERE A GMAIL OCCORRE PER PRIMA COSA CONFIGURARE IL PROPRIO ACCOUNT
# PER PERMETTERE L'ACCESSO AD APPLICAZIONI ESTERNE DA QUESTO URL:
#
# https://myaccount.google.com/lesssecureapps?pli=1
#
# POTREBBE ESSERE NECESSARIO ANCHE SBLOCCARE I CAPATCHA
#
# https://www.google.com/accounts/DisplayUnlockCaptcha
#
# ATTENZIONE QUESTO SCRIPT NON È STATO TESTATO CON ALTRI METODI
# DI SICUREZZA ATTIVATI COME L'AUTENTICAZIONE A 2 FATTORI O ATRO

import imaplib
import smtplib

from io import BytesIO
from re import compile, search
from email.parser import BytesParser
from email.policy import default

# DATI DI ACCESSO ALLA CASELLA DI POSTA GMAIL
GMAIL_USER = "<NOMEUTENTE>@gmail.com"
GMAIL_USER_PASSWORD = "<PASSWORD>"

# PARAMETRI PREDEFINITI DI GMAIL
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT   = 993
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 587

PATTERN_UID = compile("\d+ \(UID (?P<uid>\d+)\)")

def parse_uid(data):
    """Estrapola l'UID del messaggio"""
    match = PATTERN_UID.match(data)
    return match.group("uid")


def imap_connect():
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(GMAIL_USER,GMAIL_USER_PASSWORD)
    return imap


def read_folder(folder_name):

    imap = imap_connect()
    # readonly = False è utile solo se si vuole eliminare o spostare i messaggi
    imap.select(folder_name, readonly = False)

    status, data = imap.search(None, "ALL")
    if status != "OK":
        print("status", status )
        return

    # i dati vengono restituiti come unicode quindi effettuo una decodifica
    id_string = data[0].decode("ascii")

    id_list = id_string.split()   

    # PER CONVENIENZA SUCCESSIVA CONVERTO I NUMERI IN STRINGHE
    for n in [ str(x) for x in id_list ]:

        # recupero l'UID del messaggio,
        # l'UID è necessario solo per spostare o eliminare il messaggi
        # solo per leggerli non è necessario
        status, data = imap.fetch(n, "(UID)")
        if status != "OK":
            print("imap.fetch({}, (UID)) Error: {} ".format(n, status) )
            return
        else:
            # ESTRAPOLO UID DEL MESSAGGIO
            uid = parse_uid(data[0].decode("ascii"))


        # RECUPERO IL MESSAGGIO VERO E PROPRIO
        status, data = imap.fetch(n, "(RFC822)" )
        if status != "OK":
            print("imap.fetch({}, (RFC822)) Error: {} ".format(n, status) )
            return

        for response_part in data:

            if isinstance(response_part, tuple):

                # accedo al messaggio utilizzando "BytesParser"
                # perchè mi fornisce una piu' facile lettura degli header
                # rispetto ad altri metodi
                byte_mex = BytesIO( response_part[1] )
                msg = BytesParser(policy=default).parse( byte_mex )


                # DETTAGLI EMAIL
                email_id = msg["Message-ID"]
                to_email = str(msg["to"].addresses[0].addr_spec).lower()
                from_email = msg["from"].addresses[0].addr_spec
                from_display_name = msg["from"].addresses[0].display_name
                from_domain = msg["from"].addresses[0].domain
                subject = msg["subject"]

                print("")
                print("UID: {}".format(uid))
                print("email_id: {}".format(email_id))
                print("to_email: {}".format(to_email))
                print("from_email: {}".format(from_email))
                print("from_display_name: {}".format(from_display_name))
                print("from_domain: {}".format(from_domain))
                print("subject: {}".format(subject))

                if msg.is_multipart():

                    for part in msg.walk():
                        content_type =  part.get_content_type()
                        content_disposition = str(part.get('Content-Disposition'))
                        body = part.get_payload(decode=True)  # decode
                        print("\nContent Type: {} - Content Disposition: {}".format( content_type, content_disposition ) )

                        # NON STAMPO A SCHERMO IL CONTENUTO DI BODY PERCHE POTREBBE ESSERE MOLTO LUNGO IN CASO DI ALLEGATI
                        # NEL CASO DI FILE BINARY PER SALVARI OCCORRE CONVERTIRLI 
                        # body = io.BytesIO( body )

                else:
                    body = msg.get_payload(decode=True)
                    print( body.decode("utf-8") )

        input("enter")


def move_message(imap, uid, destination_folder):

    # copio il messaggio
    result = imap.uid("COPY", uid, destination_folder)
    if result[0] == "OK":
        # elimino il messaggio nella cartella precedente
        status, info = imap.uid("STORE", uid , "+FLAGS", "(\Deleted)")
        imap.expunge()


def send_message(to, subject, body):

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.login(GMAIL_USER, GMAIL_USER_PASSWORD)

    mex = "\r\n".join(
        [
            "To: %s" % to,
            "From: %s" % GMAIL_FROM_EMAIL,
            "Subject: %s" % subject,
            "", body])

    server.sendmail(GMAIL_USER, [to], mex)
    server.quit()


if __name__ == "__main__":
    # inbox è il nome della cartella "posta in entrata"
    read_folder("inbox")
