-- The names column was redundant as the information can easily be calculated
-- from the email and also it was kinda wrong for users with double names

ALTER TABlE users DROP COLUMN name;
