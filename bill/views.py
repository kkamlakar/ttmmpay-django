from django.shortcuts import render, redirect
from datetime import datetime
import pyodbc


# ---------------------------
# DATABASE CONNECTION FUNCTION
# ---------------------------

def get_connection():
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-VKRMBR2\\MSSQLSERVER01;'
        'DATABASE=ttmmpay;'
        'Trusted_Connection=yes;'
    )


# ---------------------------
# LOGIN PAGE
# ---------------------------

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT PersonName, Email, UserName
        FROM dbo.registration
        WHERE UserName=? AND Password=?
        """, (username, password))

        user = cursor.fetchone()

        if user:

            request.session['name'] = user[0]
            request.session['email'] = user[1]
            request.session['username'] = user[2]

            return redirect('ttmmpage')

        else:
            return render(request, "login.html", {"error": "Invalid username or password"})

    return render(request, "login.html")


# ---------------------------
# REGISTRATION PAGE
# ---------------------------

def register(request):

    if request.method == "POST":

        personname = request.POST.get("personname")
        email = request.POST.get("email")
        username = request.POST.get("username")
        password = request.POST.get("password")
        retype_password = request.POST.get("retype_password")

        if password != retype_password:
            return render(request, "register.html", {"error": "Passwords do not match"})

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM dbo.registration WHERE UserName=?", (username,))
        existing_user = cursor.fetchone()

        cursor.execute("SELECT * FROM dbo.registration WHERE Email=?", (email,))
        existing_email = cursor.fetchone()

        if existing_user:
            return render(request, "register.html", {"error": "Username already exists"})

        if existing_email:
            return render(request, "register.html", {"error": "Email already registered"})

        registration_datetime = datetime.now()

        cursor.execute("""
        INSERT INTO dbo.registration
        (PersonName, Email, UserName, Password, Retype_Password, RegistrationDateTime)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (personname, email, username, password, retype_password, registration_datetime))

        conn.commit()

        cursor.close()
        conn.close()

        return render(request, "register.html", {"success": "Registration successful"})

    return render(request, "register.html")


# ---------------------------
# MAIN BILL PAGE
# ---------------------------

def ttmmpage(request):

    if not request.session.get('username'):
        return redirect('login')

    message = ""

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        action = request.POST.get("action")

        # -----------------
        # CREATE BILL
        # -----------------

        if action == "create_bill":

            restaurant = request.POST.get("restaurant")
            location = request.POST.get("location")
            billtype = request.POST.get("billtype")
            billdate = request.POST.get("billdate")
            billtime = request.POST.get("billtime")
            remarks = request.POST.get("remarks")

            createddatetime = datetime.now()

            cursor.execute("""
            INSERT INTO BillMaster
            (RestaurantName, Location, BillType, BillDate, BillTime, RemarksOrNotes, CreatedDateTime)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (restaurant, location, billtype, billdate, billtime, remarks, createddatetime))

            conn.commit()

            cursor.execute("SELECT SCOPE_IDENTITY()")
            bill_id = cursor.fetchone()[0]

            message = f"Bill Created ID: {bill_id}"

        # -----------------
        # ADD PERSON
        # -----------------

        elif action == "add_person":

            person = request.POST.get("person")
            created = datetime.now()

            cursor.execute("""
            INSERT INTO BillParticipants
            (PersonName, CreatedDateTime)
            VALUES (?, ?)
            """, (person, created))

            conn.commit()

            message = "Person added"

        # -----------------
        # ADD ITEM
        # -----------------

        elif action == "add_item":

            item = request.POST.get("itemname")
            price = request.POST.get("price")
            created = datetime.now()

            cursor.execute("""
            INSERT INTO BillItems
            (ItemName, Price, CreatedDateTime)
            VALUES (?, ?, ?)
            """, (item, price, created))

            conn.commit()

            message = "Item added"

        # -----------------
        # SAVE CONSUMPTION
        # -----------------

        elif action == "save_consumption":

            cursor.execute("SELECT ItemName FROM BillItems")
            items = cursor.fetchall()

            for item in items:

                item_id = item[0]

                selected_persons = request.POST.getlist(f"consume_{item_id}")

                for person_id in selected_persons:

                    cursor.execute("""
                    INSERT INTO ItemConsumption (ItemName, PersonId)
                    VALUES (?, ?)
                    """, (item_id, person_id))

            conn.commit()

            message = "Consumption saved"

    # -----------------
    # LOAD DATA FOR PAGE
    # -----------------

    cursor.execute("SELECT ParticipantID, PersonName FROM BillParticipants")
    persons = cursor.fetchall()

    cursor.execute("SELECT ItemName, Price FROM BillItems")
    items = cursor.fetchall()

    return render(request, "ttmmpage.html", {
        "message": message,
        "persons": persons,
        "items": items
    })