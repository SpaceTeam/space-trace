1. SAML anmeldung Google
2. Upload QR Code / PDF
3. QR Code in Database
4. Einchecken für Halle pro Tag
5. Admin übersicht wer & wieviele in der Halle sind
6. Public / Live API wieviele Leute heute
7. Smart export (define sick people and get all contacts automatically traced)

// Flask

// Configurable rules

// The pyromaniac gets a fire background

# Datastructures

## Member

id: number
email: string

## Certificate (vaccination)

id: number
data: string (json?)
date: date
memberId: number(fk: member)

## Visit

id: number
date: date
memberId: number(fk: member)
