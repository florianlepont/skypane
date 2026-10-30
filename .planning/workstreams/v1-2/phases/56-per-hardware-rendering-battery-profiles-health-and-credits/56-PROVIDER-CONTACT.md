---
status: to-send
channel: unknown
providers: [adsb.fi, adsb.lol]
---

# Provider contact: multi-zone use of adsb.fi and adsb.lol

Status: **to send**. Nothing in this document has been sent. The channel is
unknown: the owner must find it (see the French section at the end).

## Draft message (English)

Subject: SkyPane, an open-source e-ink flight frame: question about multi-zone use

Hello,

SkyPane is an open-source e-ink picture frame that shows the one flight
taking off or landing near it. We use your ADS-B data to detect that flight.
Each frame downloads a rendered image of one selected flight. No feed and no
dataset is republished.

Until now the project has queried a single fixed zone (Paris-Orly). We are
moving to several zones in France, one per distinct location of a small
closed group of registered users, queried on the existing cycle of about 30
seconds. Nothing is sold; the frames belong to that small group.

Volume. Queries are shared per zone: several frames in the same zone cost
one request. We plan a global budget of at most 1 request per second across
all providers and all zones, with back-off on any error. This budget is
planned and not yet implemented. Today the project makes two requests per 30
seconds in total, one to each provider, about 0.07 requests per second.

We would be grateful for your answers to four questions:

1. Is this multi-zone, multi-user personal use acceptable under adsb.fi's
   "personal, non-commercial use only" terms, given that the frames belong
   to a small closed group and nothing is sold?
2. Is this request pattern acceptable, or would you prefer a higher-rate or
   identified arrangement?
3. For adsb.lol: will the planned feeder key requirement apply to us, and
   what is expected of a consumer that does not feed?
4. Do you have a preferred User-Agent or contact string for our requests?

Both services are credited on a public credits page, and the adsb.fi home
page is linked there.

Thank you for running these services.

## Sent / reply log

| Date | Provider | Channel | Summary |
|------|----------|---------|---------|

## Instructions pour le propriétaire (en français)

1. Cherchez le canal de contact de chaque service : pied de page, lien
   Discord ou dépôt GitHub de adsb.fi et de adsb.lol. Notez-le dans
   `channel` en tête de ce fichier.
2. Envoyez le texte anglais ci-dessus à chaque service, sans ajouter de
   coordonnées, de noms d'utilisateurs ni d'adresses e-mail.
3. Notez la date, le service, le canal et le résumé de chaque envoi, puis de
   chaque réponse, dans le tableau du journal.
4. Passez `status` à `sent` une fois les messages envoyés.
