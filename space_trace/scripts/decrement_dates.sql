UPDATE users 
SET vaccinated_till = date(vaccinated_till, '-90 days') 
WHERE vaccinated_till NOT NULL;