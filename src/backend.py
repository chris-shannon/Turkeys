import pandas as pd
from fpdf import FPDF

class Backend:

    def __init__(self,csv=0):
        if csv:
            #future for csv save
            return
        else:
            #create empty turkeys table
            self.orders = pd.DataFrame({
                "oid": pd.Series(dtype="int"),
                "name": pd.Series(dtype="string"),
                "assigned_tid": pd.Series(dtype="int"),
                "assigned_weight": pd.Series(dtype="float"),
                "target_weight": pd.Series(dtype="float"),
                "ham": pd.Series(dtype="string"),
                "notes": pd.Series(dtype="string"),
            }).set_index("oid")
            # create empty orders
            self.turkeys = pd.DataFrame({
                "tid": pd.Series(dtype="int"),
                "weight": pd.Series(dtype="float"),
                "assigned": pd.Series(dtype="bool")
            }).set_index("tid")

    def add_order(self, oid, target_weight, name, ham, notes):
        if oid in self.orders.index:
            raise ValueError(f"Order with oid={oid} already exists!")
        new_order = {
            "target_weight": target_weight,
            "name": name,
            "ham": ham,
            "notes": notes,
            "assigned_tid": pd.NA,
            "assigned_weight": pd.NA
        }

        self.orders.loc[oid] = new_order

    def add_turkey(self,tid,weight):
        if tid in self.turkeys.index:
            raise ValueError(f"turkey with tid={tid} already exists!")
        new_turkey = {
            "weight": weight,
            "assigned": False
        }
        self.turkeys.loc[tid] = new_turkey

    def match(self,oid,tid):
        # Check if turkey exists and is free
        if tid not in self.turkeys.index:
            raise ValueError(f"Turkey with tid={tid} does not exist!")
        if self.turkeys.loc[tid, "assigned"]:
            raise ValueError(f"Turkey with tid={tid} is already assigned!")

        # Check if order exists and has no turkey yet
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")
        if pd.notna(self.orders.loc[oid, "assigned_tid"]):
            raise ValueError(f"Order with oid={oid} already has a turkey assigned!")

        #perform match
             # 1. Assign turkey ID to the order
        self.orders.loc[oid, "assigned_tid"] = tid

            # 2. Assign the turkey's weight to the order
        self.orders.loc[oid, "assigned_weight"] = self.turkeys.loc[tid, "weight"]

            # 3. Mark turkey as assigned
        self.turkeys.loc[tid, "assigned"] = True

        print(f"Order {oid} matched with Turkey {tid} successfully!")

    def auto_match(self):
        print("=== AUTO MATCH START ===")

        # Only unassigned orders & turkeys
        orders = self.orders[self.orders["assigned_tid"].isna() & (self.orders["target_weight"] != 0)].copy()
        turkeys = self.turkeys[~self.turkeys["assigned"]].copy()

        if orders.empty:
            print("No unassigned orders.")
            return
        if turkeys.empty:
            print("No unassigned turkeys.")
            return

        # Sort orders by target_weight (or OID if you prefer)
        orders = orders.sort_values(by=["target_weight", "oid"])  # optional OID secondary sort

        # Sort turkeys by weight
        turkeys = turkeys.sort_values(by="weight")

        for oid, order in orders.iterrows():
            if turkeys.empty:
                print("No turkeys left to assign.")
                break

            # Find turkey with closest weight
            diffs = (turkeys["weight"] - order["target_weight"]).abs()
            tid = diffs.idxmin()
            turkey_weight = turkeys.loc[tid, "weight"]

            print(f"Assigning Order {oid} ({order['target_weight']} lbs) → Turkey {tid} ({turkey_weight} lbs)")

            # Match them
            self.match(oid, tid)

            # Remove assigned turkey
            turkeys = turkeys.drop(tid)

        print("=== AUTO MATCH END ===")

    def remove_match_by_oid(self, oid):
        # Check if order exists
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")

        # Check if order actually has a turkey assigned
        assigned_tid = self.orders.loc[oid, "assigned_tid"]
        if assigned_tid == 0:
            raise ValueError(f"Order {oid} has no turkey assigned to remove!")

        # ---------- Perform remove ----------
        # 1. Remove turkey assignment from the order
        self.orders.loc[oid, "assigned_tid"] = pd.NA
        self.orders.loc[oid, "assigned_weight"] = pd.NA
        # 2. Mark turkey as unassigned
        self.turkeys.loc[assigned_tid, "assigned"] = False

        print(f"Match removed: Order {oid} is no longer assigned to Turkey {assigned_tid}.")

    def remove_match_by_tid(self, tid):
        # Check if turkey exists
        if tid not in self.turkeys.index:
            raise ValueError(f"Turkey with tid={tid} does not exist!")

        # Check if turkey is actually assigned
        if not self.turkeys.loc[tid, "assigned"]:
            raise ValueError(f"Turkey with tid={tid} is not currently assigned to any order!")

        # Find the order that has this turkey assigned
        orders_with_tid = self.orders[self.orders["assigned_tid"] == tid]
        if orders_with_tid.empty:
            raise ValueError(f"No order found with turkey {tid} assigned!")  # should not happen if logic is correct

        # There should be only one order per turkey
        oid = orders_with_tid.index[0]

        # ---------- Perform remove ----------
        self.orders.loc[oid, "assigned_tid"] = pd.NA
        self.orders.loc[oid, "assigned_weight"] = pd.NA
        self.turkeys.loc[tid, "assigned"] = False

        print(f"Match removed: Turkey {tid} is no longer assigned to Order {oid}.")

    def remove_order(self, oid):
        # Check if order exists
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")

        assigned_tid = self.orders.loc[oid, "assigned_tid"]

        # Only unassign if a turkey is actually assigned
        if pd.notna(assigned_tid):
            self.remove_match_by_oid(oid)

        # Now safe to remove the order
        self.orders.drop(oid, inplace=True)
        print(f"Order {oid} removed from the table successfully.")

    def remove_turkey(self, tid):
        # Check if turkey exists
        if tid not in self.turkeys.index:
            raise ValueError(f"Turkey with tid={tid} does not exist!")
        # Check if turkey is assigned
        if self.turkeys.loc[tid, "assigned"]:
            self.remove_match_by_tid(tid)
        # Remove the turkey from the table
        self.turkeys.drop(tid, inplace=True)

        print(f"Turkey {tid} removed from the table successfully.")

    def list_orders(self):
        return self.orders.reset_index().to_dict(orient="records")

    def list_turkeys(self):
        return self.turkeys.reset_index().to_dict(orient="records")

    def export_turkey_orders_pdf(self, filename: str = "orders_turkey_report.pdf"):
        """
        Creates a PDF from the orders DataFrame and saves it, excluding orders with target_weight = 0.

        Args:
            filename (str): The filename for the saved PDF.
        """
        # Filter out orders with target_weight == 0
        df = self.orders[self.orders["target_weight"] != 0].sort_values(by='name')

        if df.empty:
            print("No orders with target weight > 0 to export.")
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)

        # Add a title
        pdf.cell(200, 10, txt="Orders Report", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", size=12)
        col_width = pdf.w / 6  # 6 columns
        row_height = pdf.font_size * 1.5

        headers = ["Name", "Turkey #", "Assigned lbs", "Target lbs", "Ham", "Notes"]

        # Add table header using custom names
        for header in headers:
            pdf.cell(col_width, row_height, txt=header, border=1, align="C")
        pdf.ln(row_height)

        # Add table rows
        for _, row in df.iterrows():
            row_values = [
                row["name"],
                row["assigned_tid"] if pd.notna(row["assigned_tid"]) else "",
                row["assigned_weight"] if pd.notna(row["assigned_weight"]) else "",
                row["target_weight"],
                row["ham"],
                row["notes"],
            ]
            for item in row_values:
                pdf.cell(col_width, row_height, txt=str(item), border=1, align="C")
            pdf.ln(row_height)

        # Save PDF
        pdf.output(filename)
        print(f"PDF saved as '{filename}'")

    def export_free_turkeys_pdf(self, filename: str = "free_turkeys.pdf"):
        """
        Creates a PDF listing only unassigned turkeys.
        Columns: Name, Turkey #, Assigned lbs, Target lbs, Ham, Notes
        Only Turkey # and Assigned lbs are filled; others are blank.
        """
        df = self.turkeys[self.turkeys["assigned"] == False].sort_values(by='weight')  # get unassigned turkeys

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)

        # Title
        pdf.cell(200, 10, txt="Free Turkeys Report", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", size=12)

        headers = ["Name", "Turkey #", "Assigned lbs", "Target lbs", "Ham", "Notes"]
        col_width = pdf.w / len(headers)  # divide page width evenly
        row_height = pdf.font_size * 1.5

        # Table header
        for header in headers:
            pdf.cell(col_width, row_height, txt=header, border=1, align="C")
        pdf.ln(row_height)

        # Table rows
        for tid, turkey in df.to_dict("index").items():
            row_data = ["", tid, turkey["weight"], "", "", ""]  # only Turkey # and Assigned lbs filled
            for item in row_data:
                pdf.cell(col_width, row_height, txt=str(item), border=1, align="C")
            pdf.ln(row_height)

        pdf.output(filename)
        print(f"PDF saved as '{filename}'")

    def export_ham_orders_without_turkey(self, filename: str = "ham_orders_report.pdf"):
        """
        Creates a PDF from orders that have ham and no assigned turkey.

        Args:
            filename (str): The filename for the saved PDF.
        """
        # Filter orders: ham is not 'None' and assigned_tid is NaN
        df = self.orders[
            (self.orders["ham"] != "None") & (self.orders["assigned_tid"].isna())
            ].sort_values(by="name")

        if df.empty:
            print("No ham orders without assigned turkeys.")
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)

        # Add a title
        pdf.cell(200, 10, txt="Ham Orders Without Assigned Turkeys", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", size=12)
        col_width = pdf.w / 4  # three columns + some extra space
        row_height = pdf.font_size * 1.5

        headers = ["Name", "Ham", "Notes"]

        # Table header
        for header in headers:
            pdf.cell(col_width, row_height, txt=header, border=1, align="C")
        pdf.ln(row_height)

        # Table rows
        for _, row in df.iterrows():
            row_values = [
                row["name"],
                row["ham"],
                row["notes"],
            ]
            for item in row_values:
                pdf.cell(col_width, row_height, txt=str(item), border=1, align="C")
            pdf.ln(row_height)

        # Save PDF
        pdf.output(filename)
        print(f"PDF saved as '{filename}'")

    def print_tables(self):
        print("Orders:")
        print(self.orders, "\n")
        print("Turkeys:")
        print(self.turkeys, "\n")