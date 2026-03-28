from django.shortcuts import render, redirect
from datetime import datetime
import pyodbc
import json
from django.http import JsonResponse
from collections import defaultdict



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
        
            username = request.session.get('username')
            
            cursor.execute("""
            INSERT INTO BillMaster 
            (RestaurantName, Location, BillType, BillDate, BillTime, RemarksOrNotes, CreatedDateTime, UserName)
            OUTPUT INSERTED.BillId
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "Quick Bill",
                "NA",
                "Manual",
                datetime.now().date(),
                datetime.now().time(),
                "Auto created",
                datetime.now(),
                username
            ))

            bill_id = int(cursor.fetchone()[0])

            request.session['bill_id'] = bill_id

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
        data = json.loads(request.body.decode('utf-8'))
        print("DATA RECEIVED:", data)

        username = request.session.get('username')

        restaurant = data.get("restaurantName")
        bill_date = data.get("billDate")
        bill_time = data.get("billTime")
        persons = data.get("persons", [])
        items = data.get("items", [])
        tax = data.get("tax", 0)
        tip = data.get("tip", 0)
        tax_people = data.get("taxPeople", [])
        tip_people = data.get("tipPeople", [])

        conn = get_connection()
        cursor = conn.cursor()

        # ✅ ALWAYS CREATE NEW BILL (no dependency on session)
        cursor.execute("""
        INSERT INTO BillMaster 
        (RestaurantName, Location, BillType, BillDate, BillTime, RemarksOrNotes, CreatedDateTime, UserName)
        OUTPUT INSERTED.BillId
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            restaurant if restaurant else "Quick Bill",
            "NA",
            "Manual",
            bill_date if bill_date else datetime.now().date(),
            bill_time if bill_time else datetime.now().time(),
            "Auto created",
            datetime.now(),
            username
        ))

        bill_id = int(cursor.fetchone()[0])
        conn.commit()

        person_totals = {p: 0 for p in persons}
        today = datetime.now().date()

        # INSERT ITEMS
        for item in items:
            if not item["consumed"]:
                continue

            split_price = item["price"] / len(item["consumed"])

            for person in item["consumed"]:
                person_totals[person] += split_price

                cursor.execute("""
                INSERT INTO BillSummary
                (Date, PersonName, ItemName, ItemPrice, PerPersonSplitPrice, FinalPrice, BillId, UserName)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    today,
                    person,
                    item["name"],
                    item["price"],
                    split_price,
                    0,
                    bill_id,
                    username
                ))

        # TAX
        if tax > 0 and tax_people:
            tax_per = tax / len(tax_people)
            for p in tax_people:
                if p in person_totals:
                    person_totals[p] += tax_per

        # TIP
        if tip > 0 and tip_people:
            tip_per = tip / len(tip_people)
            for p in tip_people:
                if p in person_totals:
                    person_totals[p] += tip_per

        # UPDATE FINAL
        for person, total in person_totals.items():
            cursor.execute("""
            UPDATE BillSummary
            SET FinalPrice = ?
            WHERE PersonName = ? AND BillId = ? AND UserName = ?
            """, (total, person, bill_id, username))

        conn.commit()
        cursor.close()
        conn.close()

        return JsonResponse({"status": "success", "bill_id": bill_id})

    except Exception as e:
        print("SAVE BILL ERROR:", e)
        return JsonResponse({"status": "error", "message": str(e)})
    

    
    
def summary_page(request, bill_id=None):

    conn = get_connection()
    cursor = conn.cursor()

    username = request.session.get('username')

    cursor.execute("""
        SELECT MAX(BillId)
        FROM billsummary
        WHERE UserName = ?
    """, (username,))
    max_id = cursor.fetchone()[0]

    cursor.execute("""
        SELECT MIN(BillId)
        FROM billsummary
        WHERE UserName = ?
    """, (username,))
    min_id = cursor.fetchone()[0]

    if bill_id is None:
        bill_id = max_id

    # prevent going beyond limits
    if bill_id > max_id:
        bill_id = max_id

    if bill_id < min_id:
        bill_id = min_id

    # Query 1 → item details
    username = request.session.get('username')

    cursor.execute("""
        SELECT *
        FROM billsummary
        WHERE BillId = ? AND UserName = ?
        ORDER BY PersonName, ItemName           
    """, (bill_id, username))
    rows = cursor.fetchall()

    # Query 2 → total per person
    cursor.execute("""
        SELECT PersonName, MAX(FinalPrice)
        FROM billsummary
        WHERE BillId = ? AND UserName = ?
        GROUP BY PersonName    
    """, (bill_id, username))
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




def bill_detail(request, id):

    if not request.session.get('username'):
        return redirect('login')

    conn = get_connection()
    cursor = conn.cursor()

    # Sidebar bills
    username = request.session.get('username')

    cursor.execute("""
        SELECT *
        FROM BillMaster
        WHERE BillId = ? AND UserName = ?
    """, (id, username))

    bill = cursor.fetchone()

    # NOW run sidebar query
    cursor.execute("""
        SELECT BillId, RestaurantName
        FROM BillMaster
        WHERE UserName = ?
        ORDER BY BillId DESC
    """, (username,))
    bills = cursor.fetchall()


    if not bill:
        return redirect('dashboard')

    # Persons
    cursor.execute("""
        SELECT PersonId, PersonName
        FROM BillParticipants
        WHERE BillId = ?
    """, (id,))
    persons = cursor.fetchall()

    # Items
    cursor.execute("""
        SELECT ItemId, ItemName, Price
        FROM BillItems
        WHERE BillId = ?
    """, (id,))
    items = cursor.fetchall()

    # Summary
    cursor.execute("""
        SELECT PersonName, MAX(FinalPrice)
        FROM BillSummary
        WHERE BillId = ?
        GROUP BY PersonName
    """, (id,))
    totals = cursor.fetchall()

    cursor.close()
    conn.close()

    return render(request, 'bill_detail.html', {
        'bill': bill,
        'bills': bills,
        'persons': persons,
        'items': items,
        'totals': totals
    })


def dashboard(request):
    if not request.session.get('username'):
        return redirect('login')

    username = request.session.get('username')
    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------
    # Fetch all bills for this user
    # -------------------------
    cursor.execute("""
        SELECT bm.BillId, bm.RestaurantName, bm.BillDate
        FROM BillMaster bm
        WHERE bm.UserName = ?
        ORDER BY bm.BillDate DESC, bm.BillId DESC
    """, (username,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # -------------------------
    # Main bills table
    # -------------------------
    bills_by_date = defaultdict(list)
    for bill_id, name, date in rows:
        bills_by_date[date.strftime("%Y-%m-%d")].append({
            "id": bill_id,
            "name": name
        })

    # -------------------------
    # Sidebar: group dates by year -> month -> day
    # -------------------------
    dates_by_year = defaultdict(lambda: defaultdict(list))
    for _, _, date in rows:
        if date != datetime(1900, 1, 1).date():  # ignore dummy dates
            year = date.year
            month = date.strftime("%b")  # Jan, Feb, etc.
            dates_by_year[year][month].append(date)

    # Convert nested defaultdicts to dicts for template
    dates_by_year = {y: dict(m) for y, m in dates_by_year.items()}

    # -------------------------
    # Render template
    # -------------------------
    context = {
        "bills_by_date": dict(bills_by_date),
        "dates_by_year": dates_by_year,
    }

    return render(request, 'dashboard.html', context)

