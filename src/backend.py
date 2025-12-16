import pandas as pd

class Backend:

    def __init__(self,csv=0):
        if csv:
            #future for csv save
            return
        else:
            #create empty turkeys table
            self.orders = pd.DataFrame({
                "oid": pd.Series(dtype="int"),
                "target_weight": pd.Series(dtype="float"),
                "name": pd.Series(dtype="string"),
                "ham": pd.Series(dtype="string"),
                "notes": pd.Series(dtype="string"),
                "assigned_tid": pd.Series(dtype="int"),
                "assigned_weight": pd.Series(dtype="float")
            }).set_index("oid")
            # create empty orders
            self.turkeys = pd.DataFrame({
                "tid": pd.Series(dtype="int"),
                "weight": pd.Series(dtype="float"),
                "assigned": pd.Series(dtype="bool")
            }).set_index("tid")

            return

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
        print("=== AUTO MATCH START (ORDER BUCKETS) ===")

        BUCKET_SIZE = 2
        START_WEIGHT = 8  # start at 8 lbs orders or less

        # Only unassigned orders & turkeys
        orders = self.orders[self.orders["assigned_tid"].isna()].copy()
        turkeys = self.turkeys[~self.turkeys["assigned"]]

        if orders.empty:
            print("No unassigned orders.")
            return
        if turkeys.empty:
            print("No unassigned turkeys.")
            return

        # Assign bucket to each order
        def bucket_order(weight):
            if weight <= START_WEIGHT:
                return START_WEIGHT
            return START_WEIGHT + ((weight - START_WEIGHT - 1) // BUCKET_SIZE + 1) * BUCKET_SIZE

        orders["bucket"] = orders["target_weight"].apply(bucket_order)

        # Process buckets in ascending order
        for b in sorted(orders["bucket"].unique()):
            print(f"\nProcessing bucket: {b} lbs orders")
            bucket_orders = orders[orders["bucket"] == b].sort_index()  # OID priority

            for oid, order in bucket_orders.iterrows():
                print(f"  Order {oid} target {order['target_weight']} lbs")

                if turkeys.empty:
                    print("    No turkeys left to assign.")
                    break

                # Pick smallest turkey >= target weight
                suitable = turkeys[turkeys["weight"] >= order["target_weight"]]
                if not suitable.empty:
                    tid = suitable["weight"].idxmin()
                    print(f"    Matched with turkey {tid} ({suitable.loc[tid, 'weight']} lbs)")
                else:
                    # Fallback: largest remaining turkey
                    tid = turkeys["weight"].idxmax()
                    print(f"    No suitable turkey, using largest {tid} ({turkeys.loc[tid, 'weight']} lbs)")

                # Call existing match function
                self.match(oid, tid)

                # Remove turkey from available pool
                turkeys = turkeys.drop(tid)

        print("\n=== AUTO MATCH END ===")

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
        self.orders.loc[oid, "assigned_tid"] = 0
        self.orders.loc[oid, "assigned_weight"] = 0.0

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
        self.orders.loc[oid, "assigned_tid"] = 0
        self.orders.loc[oid, "assigned_weight"] = 0.0
        self.turkeys.loc[tid, "assigned"] = False

        print(f"Match removed: Turkey {tid} is no longer assigned to Order {oid}.")

    def remove_order(self, oid):
        # Check if order exists
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")

        # If the order has a turkey assigned, remove the match
        assigned_tid = self.orders.loc[oid, "assigned_tid"]
        if assigned_tid != 0:
            self.remove_match_by_oid(oid)  # this will unassign the turkey

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

    def print_tables(self):
        print("Orders:")
        print(self.orders, "\n")
        print("Turkeys:")
        print(self.turkeys, "\n")