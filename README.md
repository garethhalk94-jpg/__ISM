*** __ISM - eCommerce Application ***

__ISM is a multi-vendor eCommerce web application built in Django. Vendors create stores
and sell products. Buyers browse and add items to their cart before checking out and 
having an invoice emailed to them, and also have the ability to leave reviews on products.
Planning Notes are available in the 'Planning' folder.


*** Features: ***

- Register and log in as a Vendor or a Buyer
- Vendors: create, view, edit and delete stores and products
- Buyers: browse and search products from the range of stores available
- Session-based shopping cart
- Checkout creates an order, reduces stock and emails an invoice
- Verified and unverified Product Reviews
- Password reset by emailed link that expires
- Permission-Based access control using Groups


*** Requirements: ***
See the file named 'requirements.txt' in the 'capitalism' directory to see
all required packages.


*** Setup ***

Run the following commands from the folder containing the file 'manage.py':

## 1. Create and activate a virtual environment:
```
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
```

## 2. Install the packages from 'requirements.txt'
```
python -m pip install -r requirements.txt
```

## 3. Create the Database:
In a MariaDB client, run the following, choosing your own password:
```sql
CREATE DATABASE capitalism CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'capitalism_user'@'localhost' IDENTIFIED BY 'your-password-here';
GRANT ALL PRIVILEGES ON capitalism.* TO 'capitalism_user'@'localhost';
FLUSH PRIVILEGES;
```

## 4. Create your '.env' file:
Create a '.env' file from the provided '.env.example' and fill in the values.
'DB_PASSWORD' must match the password used in Step 3.
Generate a secret key with:
```
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## 5. Create the tables
```
python manage.py migrate
```

## 6. Reset the Vendors and Buyers groups: *(Optional)*
The Vendors and Buyers groups are created automatically the first time
someone registers, so this step is not needed. To rebuild them at any time
(for example after editing their permissions in the admin):
```
python manage.py setup_groups
```
It should report 8 permissions for Vendors and 6 for Buyers.

## 7. Create an admin user(superuser): *(Optional)*
```
python manage.py createsuperuser
```
...and follow the prompts.

## 8. Run the server
```
python manage.py runserver
```
Open http://127.0.0.1:8000/

## REST API

The site has a JSON/XML API under `/api/v1/`. It uses **HTTP Basic
authentication**: send your site username and password with each request.
(Basic authentication is only secure over HTTPS, so use HTTPS in production.)

| Method  | Path                            | Who                   | Purpose                       |
|---------|---------------------------------|-----------------------|-------------------------------|
| POST    | `/api/v1/stores/`               | Vendors               | Create a store                |
| GET     | `/api/v1/vendors/<id>/stores/`  | Buyers, vendors       | Stores listed under a vendor  |
| GET     | `/api/v1/stores/<id>/products/` | Buyers, vendors       | Products of a store           |
| POST    | `/api/v1/stores/<id>/products/` | The store's vendor    | Add a product                 |
| GET     | `/api/v1/products/<id>/reviews/`| The product's vendor  | Retrieve its reviews          |

- **JSON** is the default. Ask for **XML** with the header
  `Accept: application/xml`.
- Status codes: `200` retrieved, `201` created, `400` invalid data,
  `401` not logged in, `403` not allowed, `404` not found.
- Example (create a store, using Python `requests`):

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/api/v1/stores/",
    auth=("your_vendor_username", "your_password"),
    json={"name": "My Store"},
)
print(response.status_code, response.json())
```

A step-by-step Postman guide is in `Postman_Testing_Guide.md`, and the design
is in `Planning/5. API Planning.md`.

## Reddit feed

`/reddit/` shows posts from a subreddit, fetched with the Python `requests`
module (`shop/functions/reddit.py`). Reddit restricts unauthenticated access to
its public feeds, so if the feed is refused the page shows the reason instead
of posts.

## Running the tests

```
python manage.py test api
```

The test runner creates a temporary database called `test_<DB_NAME>`, so the
database user needs permission for it:

```sql
GRANT ALL PRIVILEGES ON test_capitalism.* TO 'capitalism_user'@'localhost';
FLUSH PRIVILEGES;
```

## Project structure (additions)

```
api/               REST API: serializers, views, urls, tests
shop/functions/    reddit.py, the Reddit helper
```
