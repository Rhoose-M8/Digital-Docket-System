# Docket Ordering System - GUI using guizero + pyodbc
# Fully integrated with SQL Server
# Author: Rhys Bates BATESR2 2014000128


from guizero import App, Box, PushButton, Text, Combo, ListBox, TextBox, CheckBox, Window
from datetime import datetime
import pyodbc

# ----------------------------
# Database Setup
# ----------------------------
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=BATESR2Docket_System;"
    "Trusted_Connection=yes;"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# ----------------------------
# Data
# ----------------------------
category_headers = {"Entrees": "Entrees:", "Mains": "Mains:", "Desserts": "Desserts:"}
menu_items = {
    "Entrees": ["Garlic Bread", "Salt & Pepper Squid", "Pork Belly Bites"],
    "Mains": ["Pasta Carbonara", "Steak", "Blue Cod & Scallops"],
    "Desserts": ["Chocolate Brownie", "Ice Cream Sundae", "Affogato"]
}

# ----------------------------
# Helper Functions
# ----------------------------
def get_category_for_item(item):
    for cat, items in menu_items.items():
        if item in items:
            return cat
    if item.startswith("Steak"):
        return "Mains"
    if item.startswith("Ice Cream Sundae") or item.startswith("Affogato"):
        return "Desserts"
    return None

def insert_item_under_category(item_text):
    category = get_category_for_item(item_text)
    if not category:
        docket_items.append(item_text)
        return
    header_text = category_headers[category]
    if header_text not in docket_items.items:
        docket_items.append(header_text)
    idx = docket_items.items.index(header_text) + 1
    next_headers = [docket_items.items.index(h) for h in category_headers.values()
                    if h in docket_items.items and docket_items.items.index(h) > idx-1]
    if next_headers:
        next_idx = min(next_headers)
        docket_items.insert(next_idx, item_text)
    else:
        docket_items.append(item_text)

# ----------------------------
# Item Selection Functions
# ----------------------------
def add_item(item):
    if item == "Steak":
        set_steak()
    elif item == "Ice Cream Sundae":
        set_sundae()
    elif item == "Affogato":
        set_affogato()
    else:
        insert_item_under_category(item)

def set_steak():
    win = Window(app, title="Steak Doneness", width=300, height=250)
    Text(win, text="Select doneness:")
    combo = Combo(win, options=["Blue", "Rare", "Med Rare", "Med", "Med Well", "Well"], width=15)
    combo.value = "Med"
    PushButton(win, text="Save", command=lambda: (insert_item_under_category(f"Steak ({combo.value})"), win.destroy()))

def set_sundae():
    win = Window(app, title="Ice Cream Sundae Options", width=300, height=250)
    kids = CheckBox(win, text="Kids")
    Text(win, text="Sauce:")
    sauce_combo = Combo(win, options=["Chocolate", "Caramel", "Strawberry", "No Sauce"], width=15)
    sauce_combo.value = "Chocolate"
    def save():
        comment_parts = []
        if kids.value:
            comment_parts.append("Kids")
        comment_parts.append(sauce_combo.value)
        insert_item_under_category(f"Ice Cream Sundae ({', '.join(comment_parts)})")
        win.destroy()
    PushButton(win, text="Save", command=save)

def set_affogato():
    win = Window(app, title="Affogato Options", width=300, height=250)
    Text(win, text="Select type:")
    combo = Combo(win, options=["Regular", "Decaf"], width=15)
    combo.value = "Regular"
    PushButton(win, text="Save", command=lambda: (insert_item_under_category(f"Affogato ({combo.value})"), win.destroy()))

# ----------------------------
# Docket Functions
# ----------------------------
def remove_item():
    if docket_items.value and docket_items.value not in category_headers.values():
        docket_items.remove(docket_items.value)

def modify_item():
    selected = docket_items.value
    if not selected or selected in category_headers.values():
        return
    win = Window(app, title=f"Modify {selected}", width=400, height=200)
    Text(win, text=f"Modify '{selected}'")
    comment_box = TextBox(win, width=30)
    allergy_box = CheckBox(win, text="Allergy")
    def save_changes():
        comment = comment_box.value.strip()
        allergy = " ⚠️Allergy" if allergy_box.value else ""
        display_text = selected
        if comment:
            display_text += f" ({comment})"
        display_text += allergy
        idx = docket_items.items.index(selected)
        all_items = docket_items.items[:]
        all_items[idx] = display_text
        docket_items.clear()
        for item in all_items:
            docket_items.append(item)
        docket_items.value = display_text
        win.destroy()
    PushButton(win, text="Save", command=save_changes)

def place_order():
    table_num = table_number.value
    items = [i for i in docket_items.items if i not in category_headers.values()]
    if not table_num or not items:
        print("⚠️ Enter table number and at least one item.")
        return

    # 1. Get TableID
    cursor.execute("SELECT TableID FROM Table_T WHERE TableNumber=?", table_num)
    result = cursor.fetchone()
    if not result:
        print(f"⚠️ Table {table_num} not found in DB.")
        return
    table_id = result[0]

    # 2. Insert order
    order_time = datetime.now()
    cursor.execute(
        "INSERT INTO Order_T (TableID, OrderCreateTime, OrderStatus) VALUES (?, ?, ?)",
        table_id, order_time, "Active"
    )
    conn.commit()
    order_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]

    # 3. Process items
    for item_text in items:
        # Extract base meal and comment/adjustment
        if "(" in item_text:
            base_name = item_text.split("(")[0].strip()
            adjustment = item_text.split("(", 1)[1].rstrip(")").strip()
        else:
            base_name = item_text
            adjustment = None

        # 3a. Get MealID
        cursor.execute("SELECT MealID FROM Meal WHERE MealName=?", base_name)
        meal_row = cursor.fetchone()
        if not meal_row:
            print(f"Meal '{item_text}' not found in DB, skipping.")
            continue
        meal_id = meal_row[0]

        # 3b. Insert OrderItem
        cursor.execute(
            "INSERT INTO OrderItem (OrderID, MealID, QuantityOrdered) VALUES (?, ?, ?)",
            order_id, meal_id, 1
        )
        conn.commit()
        order_item_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]

        # 3c. Insert MealAdjustment if needed
        if adjustment:
            allergy_flag = 1 if "⚠️Allergy" in adjustment else 0
            adjustment_text = adjustment.replace("⚠️Allergy", "").strip()
            cursor.execute(
                "INSERT INTO MealAdjustment (OrderItemID, Adjustment, IsAllergy) VALUES (?, ?, ?)",
                order_item_id, adjustment_text, allergy_flag
            )
            conn.commit()

    # 4. Generate docket for this order
    docket_id = generate_docket_for_order(order_id)

    print(f"✅ Order placed! Table {table_num}, Items: {items}, DocketID: {docket_id}")

    # 5. Reset GUI
    docket_items.clear()
    for header in category_headers.values():
        docket_items.append(header)

# ----------------------------
# Generate Docket Function (NEW)
# ----------------------------
def generate_docket_for_order(order_id):
    cursor.execute("""
        SELECT oi.OrderItemID, m.MealName, m.MealCategoryID, m.PreparationTime
        FROM OrderItem oi
        JOIN Meal m ON oi.MealID = m.MealID
        WHERE oi.OrderID = ?
    """, order_id)

    order_items = cursor.fetchall()
    if not order_items:
        print(f"⚠️ No items for Order {order_id}.")
        return None

    max_prep_times = {}
    for item in order_items:
        cat_id = item.MealCategoryID
        prep_time = item.PreparationTime
        if cat_id not in max_prep_times or prep_time > max_prep_times[cat_id]:
            max_prep_times[cat_id] = prep_time

    time_estimate = sum(max_prep_times.values())

    cursor.execute(
        "INSERT INTO Docket (OrderID, TimeEstimate, IsGrouped, OrderSent) VALUES (?, ?, 0, 0)",
        order_id, time_estimate
    )
    conn.commit()
    docket_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
    print(f"✅ Docket {docket_id} generated for Order {order_id} (TimeEstimate={time_estimate} mins)")
    return docket_id

# ----------------------------
# Docket Screens Refresh Functions
# ----------------------------
def refresh_active_dockets():
    # Clear previous items
    for widget in screens["active_box"].children:
        widget.destroy()

    # Fetch active orders
    cursor.execute("""
        SELECT o.OrderID, t.TableNumber, o.OrderCreateTime
        FROM Order_T o
        JOIN Table_T t ON o.TableID = t.TableID
        WHERE o.OrderStatus='Active'
        ORDER BY o.OrderCreateTime
    """)
    orders = cursor.fetchall()
    print("Active orders fetched:", orders)

    # Create a box for each order
    for row_idx, (order_id, table_num, order_time) in enumerate(orders):
        # Container box for each docket
        docket_box = Box(
            screens["active_box"],
            layout="grid",
            border=True,
            width="fill",
            grid=[0, row_idx],  # crucial for display
        )

        # Calculate elapsed time
        elapsed = datetime.now() - order_time
        elapsed_text = f"{elapsed.seconds // 60} mins {elapsed.seconds % 60} secs"

        # Table info at top
        Text(
            docket_box,
            text=f"Table {table_num} | Created: {order_time.strftime('%H:%M:%S')} | Elapsed: {elapsed_text}",
            size=12,
            grid=[0, 0],
            align="left"
        )

        # Checkbox for bumping
        cb = CheckBox(docket_box, text="Select", grid=[1,0])
        cb.order_id = order_id  # attach OrderID for bump function

        # Fetch items organized by category
        cursor.execute("""
            SELECT m.MealName, mc.MealCategoryName, ma.Adjustment, ma.IsAllergy
            FROM OrderItem oi
            JOIN Meal m ON oi.MealID = m.MealID
            JOIN MealCategory mc ON m.MealCategoryID = mc.MealCategoryID
            LEFT JOIN MealAdjustment ma ON oi.OrderItemID = ma.OrderItemID
            WHERE oi.OrderID=?
            ORDER BY mc.MealCategoryName
        """, (order_id,))
        items_by_category = {}
        for meal_name, cat_name, adj, allergy in cursor.fetchall():
            line = meal_name
            if adj:
                line += f" ({adj}"
                if allergy:
                    line += " ⚠️Allergy"
                line += ")"
            items_by_category.setdefault(cat_name, []).append(line)

        # Display meals
        for i, (cat, items) in enumerate(items_by_category.items(), start=1):
            Text(docket_box, text=f"{cat}:", grid=[0, i], align="left")
            Text(docket_box, text=", ".join(items), grid=[1, i], align="left")


def refresh_archived_dockets():
    for widget in screens["archived_box"].children:
        widget.destroy()
    
    cursor.execute("""
        SELECT o.OrderID, t.TableNumber, o.OrderCreateTime
        FROM Order_T o
        JOIN Table_T t ON o.TableID = t.TableID
        WHERE o.OrderStatus='Archived'
        ORDER BY o.OrderCreateTime
    """)
    
    for order_id, table_num, order_time in cursor.fetchall():
        docket_box = Box(screens["archived_box"], layout="grid", border=True)
        elapsed = datetime.now() - order_time
        elapsed_text = f"{elapsed.seconds // 60} mins {elapsed.seconds % 60} secs"
        
        Text(docket_box, text=f"Table {table_num} | Created: {order_time.strftime('%H:%M:%S')} | Elapsed: {elapsed_text}", grid=[0,0])
        
        cursor.execute("""
            SELECT m.MealName, mc.MealCategoryName, ma.Adjustment, ma.IsAllergy
            FROM OrderItem oi
            JOIN Meal m ON oi.MealID = m.MealID
            JOIN MealCategory mc ON m.MealCategoryID = mc.MealCategoryID
            LEFT JOIN MealAdjustment ma ON oi.OrderItemID = ma.OrderItemID
            WHERE oi.OrderID=?
            ORDER BY mc.MealCategoryName
        """, order_id)
        
        items_by_category = {}
        for meal_name, cat_name, adj, allergy in cursor.fetchall():
            line = meal_name
            if adj:
                line += f" ({adj}"
                if allergy:
                    line += " ⚠️Allergy"
                line += ")"
            items_by_category.setdefault(cat_name, []).append(line)
        
        row_idx = 1
        for cat, items in items_by_category.items():
            Text(docket_box, text=f"{cat}:", grid=[0,row_idx])
            Text(docket_box, text=", ".join(items), grid=[1,row_idx])
            row_idx += 1


# ----------------------------
# Bump Order Function (Archive)
# ----------------------------
def bump_selected(selected_item):
    if not selected_item:
        return

    first_line = selected_item.split("\n")[0]
    table_num = int(first_line.split(" ")[1])

    cursor.execute("""
        SELECT o.OrderID 
        FROM Order_T o
        JOIN Table_T t ON o.TableID = t.TableID
        WHERE t.TableNumber=? AND o.OrderStatus='Active'
        ORDER BY o.OrderCreateTime
    """, table_num)

    order_id_row = cursor.fetchone()
    if not order_id_row:
        return

    order_id = order_id_row[0]
    
    # Archive the order
    cursor.execute("UPDATE Order_T SET OrderStatus='Archived' WHERE OrderID=?", order_id)
    conn.commit()
    
    # Refresh both screens automatically
    refresh_active_dockets()
    refresh_archived_dockets()

def bump_selected(selected_item, active_list, archived_list):
    if not selected_item:
        return
    first_line = selected_item.split("\n")[0]
    table_num = int(first_line.split(" ")[1])
    cursor.execute("""
        SELECT o.OrderID FROM Order_T o
        JOIN Table_T t ON o.TableID=t.TableID
        WHERE t.TableNumber=? AND o.OrderStatus='Active'
        ORDER BY o.OrderCreateTime
    """, table_num)
    order_id = cursor.fetchone()[0]
    cursor.execute("UPDATE Order_T SET OrderStatus='Archived' WHERE OrderID=?", order_id)
    conn.commit()
    # Refresh lists
    active_list.clear()
    archived_list.clear()
    refresh_active_dockets()
    refresh_archived_dockets()

def bump_selected_from_checkboxes():
    for cb in screens["active_box"].children:
        for child in cb.children.values():
            if isinstance(child, CheckBox) and child.value:
                order_id = getattr(child, "order_id", None)
                if order_id:
                    cursor.execute("UPDATE Order_T SET OrderStatus='Archived' WHERE OrderID=?", order_id)
                    conn.commit()
    refresh_active_dockets()
    refresh_archived_dockets()

# ----------------------------
# GUI Helper
# ----------------------------
def show_screen(name):
    for screen in screens.values():
        screen.hide()
    
    # Call refresh functions when showing specific screens
    if name == "active":
        refresh_active_dockets()
    elif name == "archived":
        refresh_archived_dockets()
    
    screens[name].show()

# ----------------------------
# GUI Setup
# ----------------------------
app = App("Docket Ordering System", width=800, height=900)

# Top navigation buttons
button_row = Box(app, layout="grid")
PushButton(button_row, text="Order System", command=show_screen, args=["order"], grid=[0,0])
PushButton(button_row, text="Active Dockets", command=show_screen, args=["active"], grid=[1,0])
PushButton(button_row, text="Chef’s Screen", command=show_screen, args=["chef"], grid=[2,0])
PushButton(button_row, text="Archived Dockets", command=show_screen, args=["archived"], grid=[3,0])

# Screens dictionary
screens = {}

# --- ORDER SCREEN ---
screens["order"] = Box(app)
Text(screens["order"], text="Table Number:")
table_number = Combo(screens["order"], options=[str(i) for i in range(1,21)], width=10)
table_number.value = "1"

Text(screens["order"], text="\nSelect Items:")
food_buttons = Box(screens["order"], layout="grid")
row = 0
for category, items in menu_items.items():
    Text(food_buttons, text=category, grid=[0,row])
    col = 1
    for item in items:
        PushButton(food_buttons, text=item, grid=[col,row], command=add_item, args=[item])
        col += 1
    row += 1

Text(screens["order"], text="\nCurrent Docket Items:")
docket_items = ListBox(screens["order"], items=[], width=200, height=400)
for header in category_headers.values():
    docket_items.append(header)

actions = Box(screens["order"], layout="left")
PushButton(actions, text="Modify Selected Item", command=modify_item)
PushButton(actions, text="Remove Selected Item", command=remove_item)
PushButton(actions, text="Place Order", command=place_order)

# --- ACTIVE DOCKETS SCREEN ---
screens["active"] = Box(app, layout="grid", width="fill", height=500)
Text(screens["active"], text="Active Dockets:", grid=[0,0])

# This will hold all dynamically generated docket Boxes
screens["active_box"] = Box(screens["active"], layout="grid", grid=[0,1], width="fill")

# Refresh button
PushButton(screens["active"], text="Refresh", grid=[1,0], command=refresh_active_dockets)
PushButton(screens["active"], text="Bump Selected", grid=[0,2], 
           command=lambda: bump_selected(screens["active_box"]))

# --- CHEF SCREEN ---
screens["chef"] = Box(app)
Text(screens["chef"], text="Chef’s Screen (to be developed)", grid=[0,0])

# --- ARCHIVED DOCKETS SCREEN ---
screens["archived"] = Box(app, layout="grid", width="fill", height=500)
Text(screens["archived"], text="Archived Dockets:", grid=[0,0])
screens["archived_box"] = Box(screens["archived"], layout="grid", width="fill", height=400, grid=[0,1])
PushButton(screens["archived"], text="Refresh", grid=[1,0], command=refresh_archived_dockets)


# Show order screen initially
show_screen("order")

# Start app
app.display()