from django.shortcuts import render, redirect
from datetime import datetime
import pyodbc
import json
from django.http import JsonResponse



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

            return redirect('dashboard')

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
            
            request.session['bill_id'] = int(bill_id)

            message = f"Bill Created ID: {bill_id}"

        # -----------------
        # ADD PERSON
        # -----------------

        elif action == "add_person":

            bill_id = request.session.get("bill_id")

            if not bill_id:
                message = "Please create bill first"

            else:
                person = request.POST.get("person")
                created = datetime.now()

                cursor.execute("""
                INSERT INTO BillParticipants
                (BillId, PersonName, CreatedDateTime)
                VALUES (?, ?, ?)
                """, (bill_id, person, created))

                conn.commit()

                message = "Person added"

        # -----------------
        # ADD ITEM
        # -----------------

        elif action == "add_item":

            bill_id = request.session.get("bill_id")

            if not bill_id:
                message = "Please create bill first"

            else:
                item = request.POST.get("itemname")
                price = request.POST.get("price")
                created = datetime.now()

                cursor.execute("""
                INSERT INTO BillItems
                (BillId, ItemName, Price, CreatedDateTime)
                VALUES (?, ?, ?, ?)
                """, (bill_id, item, price, created))

                conn.commit()

                message = "Item added"

        # -----------------
        # SAVE CONSUMPTION
        # -----------------

#        elif action == "save_consumption":

#            cursor.execute("SELECT ItemId FROM BillItems")
#            items = cursor.fetchall()

#            for item in items:

#                item_id = item[0]

#                selected_persons = request.POST.getlist(f"consume_{item_id}")

#                for person_id in selected_persons:

#                    cursor.execute("""
#                    INSERT INTO ItemConsumption (ItemId, PersonId)
#                    VALUES (?, ?)
#                    """, (item_id, person_id))

#            conn.commit()

#            message = "Consumption saved"

    # -----------------
    # LOAD DATA FOR PAGE
    # -----------------

    bill_id = request.session.get("bill_id", 0)

    cursor.execute("""
    SELECT PersonId, PersonName
    FROM BillParticipants
    WHERE BillId = ?
    """, (bill_id,))
    persons = cursor.fetchall()

    cursor.execute("""
    SELECT ItemId, ItemName, Price
    FROM BillItems
    WHERE BillId = ?
    """, (bill_id,))
    items = cursor.fetchall()

    person_count = len(persons)
    item_count = len(items)

    return render(request, "ttmmpage.html", {
        "message": message,
        "persons": persons,
        "items": items,
        "person_count": person_count,
        "item_count": item_count
    })


def save_bill(request):

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST required"})

    try:

        data = json.loads(request.body)

        print("DATA RECEIVED:", data)

        persons = data.get("persons", [])
        items = data.get("items", [])   
        tax = data.get("tax", 0)
        tip = data.get("tip", 0)
        tax_people = data.get("taxPeople", [])
        tip_people = data.get("tipPeople", [])

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT ISNULL(MAX(BillId),0) + 1 FROM billsummary")
        bill_id = cursor.fetchone()[0]

        person_totals = {}

        for p in persons:
            person_totals[p] = 0

        today = datetime.now().strftime("%Y-%m-%d")

        # -------------------------
        # INSERT ITEM SPLITS
        # -------------------------

        for item in items:

            item_name = item["name"]
            item_price = item["price"]
            consumers = item["consumed"]

            if len(consumers) == 0:
                continue

            split_price = item_price / len(consumers)

            for person in consumers:

                person_totals[person] += split_price

                cursor.execute("""
                INSERT INTO BillSummary
                (Date, PersonName, ItemName, ItemPrice, PerPersonSplitPrice, FinalPrice, BillId)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    today,
                    person,
                    item_name,
                    item_price,
                    split_price,
                    0,
                    bill_id
                ))
        # -------------------------
        # APPLY TAX
        # -------------------------
        if tax > 0 and len(tax_people) > 0:

            tax_per_person = tax / len(tax_people)

            for p in tax_people:
                if p in person_totals:
                    person_totals[p] += tax_per_person


        # -------------------------
        # APPLY TIP
        # -------------------------
        if tip > 0 and len(tip_people) > 0:

            tip_per_person = tip / len(tip_people)

            for p in tip_people:
                if p in person_totals:
                    person_totals[p] += tip_per_person
        # -------------------------
        # UPDATE FINAL PRICE
        # -------------------------

        for person, total in person_totals.items():

            cursor.execute("""
            UPDATE BillSummary
            SET FinalPrice = ?
            WHERE PersonName = ? AND Date = ?
            """, (total, person, today))

        conn.commit()

        cursor.close()
        conn.close()

        return JsonResponse({"status": "success"})

    except Exception as e:

        print("SAVE BILL ERROR:", e)

        return JsonResponse({"status": "error", "message": str(e)})
    

    
def summary_page(request, bill_id=None):

    conn = get_connection()
    cursor = conn.cursor()

    # get max bill id
    cursor.execute("SELECT MAX(BillId) FROM billsummary")
    max_id = cursor.fetchone()[0]

    # get min bill id
    cursor.execute("SELECT MIN(BillId) FROM billsummary")
    min_id = cursor.fetchone()[0]

    if bill_id is None:
        bill_id = max_id

    # prevent going beyond limits
    if bill_id > max_id:
        bill_id = max_id

    if bill_id < min_id:
        bill_id = min_id

    # Query 1 → item details
    cursor.execute("""
        SELECT *
        FROM billsummary
        WHERE BillId = ?
        ORDER BY PersonName, ItemName           
    """, (bill_id,))
    rows = cursor.fetchall()

    # Query 2 → total per person
    cursor.execute("""
        SELECT PersonName, MAX(FinalPrice)
        FROM billsummary
        WHERE BillId = ?
        GROUP BY PersonName    
    """, (bill_id,))
    totals = cursor.fetchall()

    cursor.close()
    conn.close()

    return render(request, "summary.html", {
        "rows": rows,
        "totals": totals,
        "bill_id": bill_id,
        "max_id": max_id,
        "min_id": min_id
    })


def dashboard(request):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT BillId, RestaurantName
        FROM BillMaster
        ORDER BY BillId DESC
    """)

    bills = cursor.fetchall()

    cursor.close()
    conn.close()

    return render(request, 'dashboard.html', {'bills': bills})

def bill_detail(request, id):

    conn = get_connection()
    cursor = conn.cursor()

    # Get all bills (for sidebar)
    cursor.execute("""
        SELECT BillId, RestaurantName
        FROM BillMaster
        ORDER BY BillId DESC
    """)
    bills = cursor.fetchall()

    # Get selected bill
    cursor.execute("""
        SELECT *
        FROM BillMaster
        WHERE BillId = ?
    """, (id,))
    bill = cursor.fetchone()

    cursor.close()
    conn.close()

    return render(request, 'bill_detail.html', {
        'bill': bill,
        'bills': bills
    })