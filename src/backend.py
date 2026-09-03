import pandas as pd
import pickle
from fpdf import FPDF
import matplotlib
matplotlib.use("Agg")  # Must be called before importing pyplot
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.ndimage import gaussian_filter1d
from scipy.ndimage import uniform_filter1d

class Backend:

    def __init__(self):
            #create empty turkeys table
            self.orders = pd.DataFrame({
                "oid": pd.Series(dtype="int"),
                "name": pd.Series(dtype="string"),
                "assigned_tid": pd.Series(dtype="int"),
                "assigned_weight": pd.Series(dtype="float"),
                "target_weight": pd.Series(dtype="float"),
                "ham": pd.Series(dtype="string"),
                "notes": pd.Series(dtype="string"),
                "displacement":pd.Series(dtype="float")
            }).set_index("oid")
            # create empty orders
            self.turkeys = pd.DataFrame({
                "tid": pd.Series(dtype="int"),
                "weight": pd.Series(dtype="float"),
                "assigned": pd.Series(dtype="bool")
            }).set_index("tid")

    def save(self, path):
        with open(path, "wb") as file:
            pickle.dump({"orders": self.orders, "turkeys": self.turkeys}, file)

    def load(self, path):
        with open(path, "rb") as file:
            data = pickle.load(file)

        self.orders = data["orders"]
        self.turkeys = data["turkeys"]

        # 🔹 Ensure new columns exist (backward compatibility)
        if "displacement" not in self.orders.columns:
            self.orders["displacement"] = pd.NA
        print("Orders columns:", self.orders.columns.tolist())
        print(self.orders.iloc[:2])

        print("Turkeys columns:", self.turkeys.columns.tolist())
        print(self.orders.iloc[:2])

    def add_order(self, oid, target_weight, name, ham, notes):
        if oid in self.orders.index:
            raise ValueError(f"Order with oid={oid} already exists!")
        new_order = {
            "target_weight": target_weight,
            "name": name,
            "ham": ham,
            "notes": notes,
            "assigned_tid": pd.NA,
            "assigned_weight": pd.NA,
            "displacement": pd.NA
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

    def match_closest(self, oid):
        # Check if order exists
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")

        # Check if order already has a turkey
        if pd.notna(self.orders.loc[oid, "assigned_tid"]):
            raise ValueError(f"Order with oid={oid} already has a turkey assigned!")

        # Get requested weight
        requested_weight = self.orders.loc[oid, "target_weight"]

        # Get available turkeys
        available_turkeys = self.turkeys[self.turkeys["assigned"] == False]

        if available_turkeys.empty:
            raise ValueError("No available turkeys left to assign!")

        # Find turkey with closest weight
        closest_tid = (
            (available_turkeys["weight"] - requested_weight)
            .abs()
            .idxmin()
        )

        # Perform match (reuse your logic)
        self.match(oid,closest_tid)

        print(
            f"Order {oid} matched with Turkey {closest_tid} "
            f"(weight={self.turkeys.loc[closest_tid, 'weight']}) successfully!"
        )

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
            # 4. Generate displacement
        self.orders.loc[oid, "displacement"] = self.orders.loc[oid, "assigned_weight"]-self.orders.loc[oid, "target_weight"]

        print(f"Order {oid} matched with Turkey {tid} successfully!")

    def swap_orders(self, oid1, oid2):
        # Ensure both orders exist
        if oid1 not in self.orders.index or oid2 not in self.orders.index:
            raise ValueError("One or both orders do not exist!")

        # Swap assigned turkey IDs
        self.orders.loc[[oid1, oid2], ["assigned_tid"]] = self.orders.loc[[oid2, oid1], ["assigned_tid"]].values

        # Swap assigned weights
        self.orders.loc[[oid1, oid2], ["assigned_weight"]] = self.orders.loc[[oid2, oid1], ["assigned_weight"]].values

        # Swap displacement values
        for oid in [oid1, oid2]:
            self.orders.loc[oid, "displacement"] = abs(
                self.orders.loc[oid, "assigned_weight"] - self.orders.loc[oid, "target_weight"]
            )
        print(f"Orders {oid1} and {oid2} have been swapped.")

    import numpy as np
    import pandas as pd
    from scipy.ndimage import uniform_filter1d

    def test_delta(self, delta, alpha=0.1):
        """
        Test if all orders can be matched within +/- delta,
        using weighted scarcity to prioritize hardest orders first.

        alpha: weight factor for distance to closest feasible turkey
        """
        # Reset assignments
        self.orders["assigned_tid"] = pd.NA
        self.turkeys["assigned"] = False

        # Add OID tie-breaker column (if not already present)
        if "_oid" not in self.orders.columns:
            self.orders["_oid"] = self.orders.index

        self.orders["matching_score"] = 0

        while self.orders["assigned_tid"].isna().any():
            unassigned = self.orders[self.orders["assigned_tid"].isna()]
            if unassigned.empty:
                break

            # Step 1: Compute weighted scarcity score for unassigned orders
            for oid in unassigned.index:
                target = self.orders.loc[oid, "target_weight"]

                # feasible turkeys within delta
                feasible = self.turkeys[
                    (~self.turkeys["assigned"]) &
                    (self.turkeys["weight"] >= target - delta) &
                    (self.turkeys["weight"] <= target + delta)
                    ]

                count = len(feasible)

                if feasible.empty:
                    # No turkey can satisfy this order
                    self.orders.loc[oid, "matching_score"] = np.inf
                else:
                    # distance to closest feasible turkey
                    min_dist = abs(feasible["weight"] - target).min()
                    # weighted scarcity: fewer options + farther closest turkey
                    self.orders.loc[oid, "matching_score"] = count + alpha * min_dist

            # Step 2: Pick the hardest order (lowest score), tie-break by OID
            sorted_unassigned = unassigned.sort_values(
                ["matching_score", "_oid"],
                ascending=[True, True]
            )
            oid = sorted_unassigned.index[0]

            target = self.orders.loc[oid, "target_weight"]
            available = self.turkeys[~self.turkeys["assigned"]]

            # Step 3: Enforce delta when selecting turkey
            feasible = available[
                (available["weight"] >= target - delta) &
                (available["weight"] <= target + delta)
                ]

            if feasible.empty:
                # Delta too small
                return False

            # Step 4: Pick closest feasible turkey
            best_tid = (feasible["weight"] - target).abs().idxmin()
            self.match(oid, best_tid)

        # All orders assigned successfully
        return True

    def auto_match(self, low=0.0, high=3.0, tol=0.1):
        best = None

        while high - low > tol:
            mid = (low + high) / 2
            print(f"Trying delta = {mid:.2f}")

            if self.test_delta(mid):
                best = mid
                high = mid  # try smaller delta
            else:
                low = mid  # need larger delta

        return round(best, 1) if best is not None else None

        raise RuntimeError("No delta found that matches all orders")

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
        self.orders.loc[oid, "displacement"] = pd.NA
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
        self.orders.loc[oid, "displacement"] = pd.NA
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
        Creates a PDF from the orders DataFrame and saves it,
        excluding orders with target_weight = 0.
        """

        df = self.orders[self.orders["target_weight"] != 0].sort_values(by="name")

        if df.empty:
            print("No orders with target weight > 0 to export.")
            return

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        headers = ["Name", "#", "Assigned lbs", "Target lbs", "Ham", "Notes"]

        # Match column proportions from Free Turkeys report
        col_widths = [
            pdf.w * 0.22,  # Name
            pdf.w * 0.08,  # Turkey #
            pdf.w * 0.15,  # Assigned lbs
            pdf.w * 0.15,  # Target lbs
            pdf.w * 0.10,  # Ham
            pdf.w * 0.30,  # Notes
        ]

        ROW_HEIGHT = 9

        def draw_header():
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 12, "Orders Report", ln=True, align="C")
            pdf.ln(6)

            pdf.set_font("Arial", "B", 13)
            for header, width in zip(headers, col_widths):
                pdf.cell(width, ROW_HEIGHT, header, border=1, align="C")
            pdf.ln(ROW_HEIGHT)

            pdf.set_font("Arial", size=12)

        draw_header()

        for _, row in df.iterrows():
            if pdf.get_y() + ROW_HEIGHT > pdf.page_break_trigger:
                pdf.add_page()
                draw_header()

            row_data = [
                row["name"],
                row["assigned_tid"] if pd.notna(row["assigned_tid"]) else "",
                row["assigned_weight"] if pd.notna(row["assigned_weight"]) else "",
                row["target_weight"],
                row["ham"],
                row["notes"],
            ]

            for item, width in zip(row_data, col_widths):
                pdf.cell(width, ROW_HEIGHT, str(item), border=1, align="C")
            pdf.ln(ROW_HEIGHT)

        pdf.output(filename)
        print(f"PDF saved as '{filename}'")

    from fpdf import FPDF

    from fpdf import FPDF

    def export_free_turkeys_pdf(self, filename: str = "free_turkeys.pdf"):
        df = self.turkeys[self.turkeys["assigned"] == False].sort_values(by="weight")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        headers = ["Name", "#", "Assigned lbs", "Target lbs", "Ham", "Notes"]

        # Custom column widths (must sum <= page width)
        col_widths = [
            pdf.w * 0.22,  # Name
            pdf.w * 0.08,  # Turkey #
            pdf.w * 0.15,  # Assigned lbs
            pdf.w * 0.15,  # Target lbs
            pdf.w * 0.10,  # Ham
            pdf.w * 0.30,  # Notes
        ]

        ROW_HEIGHT = 9

        def draw_header():
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 12, "Free Turkeys Report", ln=True, align="C")
            pdf.ln(6)

            pdf.set_font("Arial", "B", 13)
            for header, width in zip(headers, col_widths):
                pdf.cell(width, ROW_HEIGHT, header, border=1, align="C")
            pdf.ln(ROW_HEIGHT)

            pdf.set_font("Arial", size=12)

        draw_header()

        for tid, turkey in df.to_dict("index").items():
            if pdf.get_y() + ROW_HEIGHT > pdf.page_break_trigger:
                pdf.add_page()
                draw_header()

            row_data = ["", tid, turkey["weight"], "", "", ""]
            for item, width in zip(row_data, col_widths):
                pdf.cell(width, ROW_HEIGHT, str(item), border=1, align="C")
            pdf.ln(ROW_HEIGHT)

        pdf.output(filename)
        print(f"PDF saved as '{filename}'")

    def export_ham_orders_without_turkey(self, filename: str = "ham_orders_report.pdf"):
        """
        Creates a PDF from orders that have ham and no assigned turkey.
        """

        # 🔹 NEW: count hams from ALL rows
        ham_counts = (
            self.orders[self.orders["ham"] != "None"]["ham"]
            .value_counts()
            .sort_index()
        )

        # Filter orders for export
        df = self.orders[
            (self.orders["ham"] != "None") & (self.orders["assigned_tid"].isna())
            ].sort_values(by="name")

        if df.empty:
            print("No ham orders without assigned turkeys.")
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)

        # Title
        pdf.cell(200, 10, txt="Ham Orders Without Assigned Turkeys", ln=True, align="C")
        pdf.ln(5)

        # 🔹 Ham totals section (ALL rows)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, txt="Total Hams Needed (All Orders):", ln=True)

        pdf.set_font("Arial", size=11)
        for ham, count in ham_counts.items():
            pdf.cell(0, 7, txt=f"{ham}: {count}", ln=True)

        pdf.ln(8)

        # Table setup
        pdf.set_font("Arial", "B", 12)
        col_width = pdf.w / 4
        row_height = pdf.font_size * 1.5

        headers = ["Name", "Ham", "Notes"]

        # Table header
        for header in headers:
            pdf.cell(col_width, row_height, txt=header, border=1, align="C")
        pdf.ln(row_height)

        pdf.set_font("Arial", size=11)

        # Table rows (filtered only)
        for _, row in df.iterrows():
            for item in (row["name"], row["ham"], row["notes"]):
                pdf.cell(col_width, row_height, txt=str(item), border=1, align="C")
            pdf.ln(row_height)

        pdf.output(filename)
        print(f"PDF saved as '{filename}'")

    def plot_smoothed_distribution(self, bin_size=0.5, sigma=2.0, filename="assets/smoothed_distribution.png"):
        """
        Plot smoothed mismatch between turkey weights and order target weights.
        """
        if self.turkeys.empty or self.orders.empty:
            print("No data to plot.")
            return

        # Combine all weights to define bins
        all_weights = pd.concat([self.turkeys["weight"], self.orders["target_weight"]])
        min_weight = np.floor(all_weights.min())
        max_weight = np.ceil(all_weights.max())
        bins = np.arange(min_weight, max_weight + bin_size, bin_size)

        # Compute histogram counts
        turkey_counts, _ = np.histogram(self.turkeys["weight"], bins=bins)
        order_counts, _ = np.histogram(self.orders["target_weight"], bins=bins)

        # Mismatch per bin
        mismatch = order_counts - turkey_counts

        # Smooth mismatch
        smoothed_mismatch = gaussian_filter1d(mismatch.astype(float), sigma=sigma)

        # Bin centers for plotting
        bin_centers = bins[:-1] + bin_size / 2

        # Plot
        plt.figure(figsize=(12, 6))
        plt.bar(bin_centers - 0.1, turkey_counts, width=0.2, color="orange", label="Turkeys")
        plt.bar(bin_centers + 0.1, order_counts, width=0.2, color="blue", label="Orders")
        plt.plot(bin_centers, smoothed_mismatch, color="red", linewidth=2, label="Smoothed Mismatch")

        plt.xlabel("Weight (lbs)")
        plt.ylabel("Count / Mismatch")
        plt.title("Turkey vs Order Distribution with Smoothed Mismatch")
        plt.xticks(bins, rotation=90)
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.legend()
        plt.tight_layout()

        # Save plot as PNG
        plt.savefig(filename)
        print(f"Smoothed distribution plot saved as {filename}")

    def plot_turkey_order_distribution(self, filename="assets/turkey_order_distribution.png"):
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd

        if self.turkeys.empty or self.orders.empty:
            print("No data to plot.")
            return

        # Combine weights to get min/max for bins
        all_weights = pd.concat([self.turkeys["weight"], self.orders["target_weight"]])

        # Create bins of 0.5 lb
        min_weight = np.floor(all_weights.min())
        max_weight = np.ceil(all_weights.max())
        bins = np.arange(min_weight, max_weight + 0.5, 0.5)
        bin_centers = bins[:-1] + 0.25

        # Compute histogram counts
        turkey_counts, _ = np.histogram(self.turkeys["weight"], bins=bins)
        order_counts, _ = np.histogram(self.orders["target_weight"], bins=bins)

        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

        # Turkey weights line plot
        ax1.plot(bin_centers, turkey_counts, marker='o', linestyle='-', color="orange", label="Turkeys")
        ax1.set_ylabel("Count")
        ax1.set_title("Turkey Weights Distribution")
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        ax1.legend()

        # Order target weights line plot
        ax2.plot(bin_centers, order_counts, marker='s', linestyle='-', color="blue", label="Orders")
        ax2.set_xlabel("Weight (lbs)")
        ax2.set_ylabel("Count")
        ax2.set_title("Order Target Weights Distribution")
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        ax2.legend()

        plt.xticks(bins, rotation=90)
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        print(f"Two-subplot distribution saved as {filename}")

    # Example usage:
    # plot_turkey_order_distribution(self.turkeys, self.orders, filename="assets/turkey_dist.png")

    def print_tables(self):
        print("Orders:")
        print(self.orders, "\n")
        print("Turkeys:")
        print(self.turkeys, "\n")