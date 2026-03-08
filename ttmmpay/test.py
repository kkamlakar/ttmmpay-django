import pyodbc

# Replace YOUR_SERVER_NAME with your SQL Server instance name
# If you use SQL login, replace Trusted_Connection with UID/PWD
conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=DESKTOP-VKRMBR2\\MSSQLSERVER01;'
            'DATABASE=ttmmpay;'
            'Trusted_Connection=yes;'
)

cursor = conn.cursor()

# Test query to check if the table is accessible
cursor.execute("SELECT TOP 5 * FROM dbo.registration")

rows = cursor.fetchall()
for row in rows:
    print(row)

cursor.close()
conn.close()