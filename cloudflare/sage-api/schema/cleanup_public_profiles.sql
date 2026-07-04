UPDATE api_keys
SET
  display_name = REPLACE(display_name, '+', ''),
  username = REPLACE(username, '+', '')
WHERE display_name LIKE '%+%' OR username LIKE '%+%';
