Apologies, the previous README.md was an outdated copy.

# `__ISM` - eCommerce Application

__ISM is a multi-vendor eCommerce web application built in Django. Vendors create stores
and sell products. Buyers browse and add items to their cart before checking out and 
having an invoice emailed to them, and also have the ability to leave reviews on products.
Planning Notes are available in the 'Planning' folder.


# Features

- Register and log in as a **Vendor** or a **Buyer**
- Vendors: create, view, edit and delete stores and products
- Buyers: browse and search products from the range of stores available
- Session-based shopping cart
- Checkout creates an order, reduces stock and emails an invoice
- Verified and unverified Product Reviews
- Password reset by emailed link that expires
- Permission-Based access control using Groups


# Requirements

Python 3.12 or newer,
Django 6.1.2,
MariaDB 10.11 or newer,
Git (any up to date version)

Install the dependencies **only** from `requirements.txt` (step 3 below), so
your versions match the ones the project was built and tested with.


# Setup

Every step has commands you can copy and paste. Run them in a terminal
(PowerShell on Windows, Terminal on macOS or Linux).

## 1. Get the code and enter the project directory

Open you CommandPrompt/PowerShell in the directory you wish to install
and enter in the following:
```
git clone https://github.com/garethhalk94-jpg/__ISM.git
cd __ISM
```

`git clone` downloads the project into a new folder.
`cd` moves you into the project folder, the one that contains `manage.py`. 
Check you are in the right directory: enter the following and the list that
shows must include `manage.py`.

**Windows (PowerShell)**

```
dir
```

**macOS or Linux**

```
ls
```
**Stay in this folder for all the steps below.**

## 2. Create and activate a virtual environment

The command below creates a folder called `venv` **inside the project folder**.
It keeps this project's packages separate from the rest of your computer.

**Windows (PowerShell)**
```
python -m venv venv
venv\Scripts\Activate
```

**macOS or Linux**
```
python3 -m venv venv
source venv/bin/activate
```

When it works, `(venv)` appears at the start of your terminal line.

## 3. Installing Requirements

```
python -m pip install -r requirements.txt
```

If `mysqlclient` fails to install on macOS or Linux, it needs a few system
packages first:

```
# macOS (Homebrew)
brew install mysql-client pkg-config

# Debian or Ubuntu
sudo apt install python3-dev default-libmysqlclient-dev build-essential pkg-config
```

Then run the install command again.

## 4. Create the Database

You need MariaDB installed and running.

1. Open a MariaDB prompt:
    - **Windows:** Start menu, then **MariaDB CommandPrompt**. 
        It asks you for the root password you chose when you installed MariaDB.
        Alternatively you can use `mysql -u root -p` in your CommandPrompt/PowerShell.
    - **macOS:** `mysql -u root -p`
    - **Linux:** `sudo mysql`

2. Enter the following, making sure to change `your-password-here` with a password of your choice.
**IMPORTANT:** Use the **same** password for `DB_PASSWORD` in the `.env` file in Step 5.

```sql
   CREATE DATABASE capitalism CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'capitalism_user'@'localhost' IDENTIFIED BY 'your-password-here';
   GRANT ALL PRIVILEGES ON capitalism.* TO 'capitalism_user'@'localhost';
   GRANT ALL PRIVILEGES ON test_capitalism.* TO 'capitalism_user'@'localhost';
   FLUSH PRIVILEGES;
```

3. Type `exit` to leave the prompt.

## 5. Create your `.env` file

The `.env` file holds your private settings. It is not stored in Git.
**IMPORTANT:** `DB_PASSWORD` must match the password used in Step 4.

**Windows (PowerShell)**
```
Copy-Item .env.example .env
```

**macOS or Linux**
```
cp .env.example .env
```

Generate a secret key and copy the line it prints:
```
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Open `.env` in a text editor and fill it in:
```
SECRET_KEY='paste-the-generated-key-here'
DB_NAME=capitalism
DB_USER=capitalism_user
DB_PASSWORD=the-password-you-chose-in-step-4
DB_HOST=localhost
DB_PORT=3306
```

Keep the single quotes around the secret key, and no spaces around `=`.

## 6. Create the tables
```
python manage.py migrate
```

No other set-up is needed. The **Vendors** and **Buyers** groups are created
automatically the first time someone registers.

## 7. Start the site
```
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser. Stop the server with `Ctrl+C` in the terminal.


## *(OPTIONAL)* Reset the Vendors and Buyers groups:
The Vendors and Buyers groups are created automatically the first time
someone registers, so this step is not needed. To rebuild them at any time
(for example after editing their permissions in the admin):
```
python manage.py setup_groups
```
It should report 8 permissions for Vendors and 6 for Buyers.

## *(OPTIONAL)* Create an admin user (superuser):
```
python manage.py createsuperuser
```
...and follow the prompts.


# Using the site

1. Open http://127.0.0.1:8000/accounts/register/ and register a **vendor**.
2. Click **Create Store**, then **Add Product** (give it a price and some stock).
3. Log out. In a private browser window, or after logging out, register a
   **buyer**.
4. As the buyer, open **Browse Products**, open the product, add it to the cart
   and check out.
5. The invoice appears on screen and is also printed in the terminal that is
   running the server.
6. Open the product again and leave a review. It is marked **Verified**, because
   this buyer purchased it. Otherwise the review is marked **Unverified**.

- **Buyers** can open **Vendors**, **Stores** and **Browse Products** from the
  menu, and can edit or delete their own reviews on a product page.
- **Vendors** have **My Stores**, **My Products** and **My Reviews**. My
  Reviews lists the reviews of all their products, newest first, and can be
  filtered by store, rating and verified status.

# Emails

No real email is sent. While developing, emails (the invoice and password reset
links) are printed in the terminal window that is running
`python manage.py runserver`, not in the browser.

This is set in `capitalism/settings.py` and works with the pinned Django
version and with older ones.


# Running Tests
```
python manage.py test --noinput
```

The test create a temporary database called `test_capitalism` for testing.
