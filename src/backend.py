import pandas as pd
import pickle
from fpdf import FPDF
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.ndimage import gaussian_filter1d


class Backend:

    def __init__(self):
        self.orders = pd.DataFrame({
            "oid": pd.Series(dtype="int"),
            "name": pd.Series(dtype="string"),
            "assigned_tid": pd.Series(dtype="int"),
            "assigned_weight": pd.Series(dtype="float"),
            "target_weight": pd.Series(dtype="float"),
            "ham": pd.Series(dtype="string"),
            "notes": pd.Series(dtype="string"),
            "displacement": pd.Series(dtype="float")
        }).set_index("oid")

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
        if "displacement" not in self.orders.columns:
            self.orders["displacement"] = pd.NA

    def add_order(self, oid, target_weight, name, ham, notes):
        if oid in self.orders.index:
            raise ValueError(f"Order with oid={oid} already exists!")
        self.orders.loc[oid] = {
            "target_weight": target_weight,
            "name": name,
            "ham": ham,
            "notes": notes,
            "assigned_tid": pd.NA,
            "assigned_weight": pd.NA,
            "displacement": pd.NA
        }

    def add_turkey(self, tid, weight):
        if tid in self.turkeys.index:
            raise ValueError(f"Turkey with tid={tid} already exists!")
        self.turkeys.loc[tid] = {"weight": weight, "assigned": False}

    def match_closest(self, oid):
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")
        if pd.notna(self.orders.loc[oid, "assigned_tid"]):
            raise ValueError(f"Order with oid={oid} already has a turkey assigned!")

        requested_weight = self.orders.loc[oid, "target_weight"]
        available_turkeys = self.turkeys[self.turkeys["assigned"] == False]

        if available_turkeys.empty:
            raise ValueError("No available turkeys left to assign!")

        closest_tid = (available_turkeys["weight"] - requested_weight).abs().idxmin()
        self.match(oid, closest_tid)

    def match(self, oid, tid):
        if tid not in self.turkeys.index:
            raise ValueError(f"Turkey with tid={tid} does not exist!")
        if self.turkeys.loc[tid, "assigned"]:
            raise ValueError(f"Turkey with tid={tid} is already assigned!")
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")
        if pd.notna(self.orders.loc[oid, "assigned_tid"]):
            raise ValueError(f"Order with oid={oid} already has a turkey assigned!")

        self.orders.loc[oid, "assigned_tid"] = tid
        self.orders.loc[oid, "assigned_weight"] = self.turkeys.loc[tid, "weight"]
        self.turkeys.loc[tid, "assigned"] = True
        self.orders.loc[oid, "displacement"] = self.orders.loc[oid, "assigned_weight"] - self.orders.loc[oid, "target_weight"]

    def swap_orders(self, oid1, oid2):
        if oid1 not in self.orders.index or oid2 not in self.orders.index:
            raise ValueError("One or both orders do not exist!")
        self.orders.loc[[oid1, oid2], ["assigned_tid"]] = self.orders.loc[[oid2, oid1], ["assigned_tid"]].values
        self.orders.loc[[oid1, oid2], ["assigned_weight"]] = self.orders.loc[[oid2, oid1], ["assigned_weight"]].values
        for oid in [oid1, oid2]:
            self.orders.loc[oid, "displacement"] = abs(
                self.orders.loc[oid, "assigned_weight"] - self.orders.loc[oid, "target_weight"]
            )

    def test_delta(self, delta):
        self.orders["assigned_tid"] = pd.NA
        self.turkeys["assigned"] = False

        order_ids = self.orders.index.tolist()
        turkey_ids = self.turkeys.index.tolist()

        targets = self.orders["target_weight"].values
        weights = self.turkeys["weight"].values

        # Build cost matrix: rows=orders, cols=turkeys
        cost_matrix = np.abs(targets[:, None] - weights[None, :])
        cost_matrix[cost_matrix > delta] = np.inf

        # Hungarian algorithm finds the minimum total displacement assignment
        cost_finite = np.where(np.isinf(cost_matrix), 1e9, cost_matrix)
        row_ind, col_ind = linear_sum_assignment(cost_finite)

        # Reject if any assigned pair falls outside delta
        if np.any(np.isinf(cost_matrix[row_ind, col_ind])):
            return False

        for r, c in zip(row_ind, col_ind):
            self.match(order_ids[r], turkey_ids[c])

        return True

    def auto_match(self, low=0.0, high=3.0, tol=0.1):
        best = None

        while high - low > tol:
            mid = (low + high) / 2
            if self.test_delta(mid):
                best = mid
                high = mid
            else:
                low = mid

        if best is not None:
            self.test_delta(best)

        return round(best, 1) if best is not None else None

    def remove_match_by_oid(self, oid):
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")
        assigned_tid = self.orders.loc[oid, "assigned_tid"]
        if assigned_tid == 0:
            raise ValueError(f"Order {oid} has no turkey assigned to remove!")
        self.orders.loc[oid, "assigned_tid"] = pd.NA
        self.orders.loc[oid, "assigned_weight"] = pd.NA
        self.orders.loc[oid, "displacement"] = pd.NA
        self.turkeys.loc[assigned_tid, "assigned"] = False

    def remove_match_by_tid(self, tid):
        if tid not in self.turkeys.index:
            raise ValueError(f"Turkey with tid={tid} does not exist!")
        if not self.turkeys.loc[tid, "assigned"]:
            raise ValueError(f"Turkey with tid={tid} is not currently assigned to any order!")
        orders_with_tid = self.orders[self.orders["assigned_tid"] == tid]
        if orders_with_tid.empty:
            raise ValueError(f"No order found with turkey {tid} assigned!")
        oid = orders_with_tid.index[0]
        self.orders.loc[oid, "assigned_tid"] = pd.NA
        self.orders.loc[oid, "assigned_weight"] = pd.NA
        self.orders.loc[oid, "displacement"] = pd.NA
        self.turkeys.loc[tid, "assigned"] = False

    def remove_order(self, oid):
        if oid not in self.orders.index:
            raise ValueError(f"Order with oid={oid} does not exist!")
        if pd.notna(self.orders.loc[oid, "assigned_tid"]):
            self.remove_match_by_oid(oid)
        self.orders.drop(oid, inplace=True)

    def remove_turkey(self, tid):
        if tid not in self.turkeys.index:
            raise ValueError(f"Turkey with tid={tid} does not exist!")
        if self.turkeys.loc[tid, "assigned"]:
            self.remove_match_by_tid(tid)
        self.turkeys.drop(tid, inplace=True)

    def list_orders(self):
        return self.orders.reset_index().to_dict(orient="records")

    def list_turkeys(self):
        return self.turkeys.reset_index().to_dict(orient="records")

    def export_turkey_orders_pdf(self, filename: str = "orders_turkey_report.pdf"):
        df = self.orders[self.orders["target_weight"] != 0].sort_values(by="name")
        if df.empty:
            return

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        headers = ["Name", "#", "Assigned lbs", "Target lbs", "Ham", "Notes"]
        col_widths = [pdf.w * 0.22, pdf.w * 0.08, pdf.w * 0.15, pdf.w * 0.15, pdf.w * 0.10, pdf.w * 0.30]
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

    def export_free_turkeys_pdf(self, filename: str = "free_turkeys.pdf"):
        df = self.turkeys[self.turkeys["assigned"] == False].sort_values(by="weight")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        headers = ["Name", "#", "Assigned lbs", "Target lbs", "Ham", "Notes"]
        col_widths = [pdf.w * 0.22, pdf.w * 0.08, pdf.w * 0.15, pdf.w * 0.15, pdf.w * 0.10, pdf.w * 0.30]
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

    def export_ham_orders_without_turkey(self, filename: str = "ham_orders_report.pdf"):
        ham_counts = (
            self.orders[self.orders["ham"] != "None"]["ham"]
            .value_counts()
            .sort_index()
        )
        df = self.orders[
            (self.orders["ham"] != "None") & (self.orders["assigned_tid"].isna())
        ].sort_values(by="name")

        if df.empty:
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, txt="Ham Orders Without Assigned Turkeys", ln=True, align="C")
        pdf.ln(5)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, txt="Total Hams Needed (All Orders):", ln=True)
        pdf.set_font("Arial", size=11)
        for ham, count in ham_counts.items():
            pdf.cell(0, 7, txt=f"{ham}: {count}", ln=True)
        pdf.ln(8)

        pdf.set_font("Arial", "B", 12)
        col_width = pdf.w / 4
        row_height = pdf.font_size * 1.5
        for header in ["Name", "Ham", "Notes"]:
            pdf.cell(col_width, row_height, txt=header, border=1, align="C")
        pdf.ln(row_height)

        pdf.set_font("Arial", size=11)
        for _, row in df.iterrows():
            for item in (row["name"], row["ham"], row["notes"]):
                pdf.cell(col_width, row_height, txt=str(item), border=1, align="C")
            pdf.ln(row_height)

        pdf.output(filename)

    def plot_smoothed_distribution(self, bin_size=0.5, sigma=2.0, filename="assets/smoothed_distribution.png"):
        if self.turkeys.empty or self.orders.empty:
            return

        all_weights = pd.concat([self.turkeys["weight"], self.orders["target_weight"]])
        min_weight = np.floor(all_weights.min())
        max_weight = np.ceil(all_weights.max())
        bins = np.arange(min_weight, max_weight + bin_size, bin_size)

        turkey_counts, _ = np.histogram(self.turkeys["weight"], bins=bins)
        order_counts, _ = np.histogram(self.orders["target_weight"], bins=bins)
        mismatch = order_counts - turkey_counts
        smoothed_mismatch = gaussian_filter1d(mismatch.astype(float), sigma=sigma)
        bin_centers = bins[:-1] + bin_size / 2

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
        plt.savefig(filename)

    def plot_turkey_order_distribution(self, filename="assets/turkey_order_distribution.png"):
        if self.turkeys.empty or self.orders.empty:
            return

        all_weights = pd.concat([self.turkeys["weight"], self.orders["target_weight"]])
        min_weight = np.floor(all_weights.min())
        max_weight = np.ceil(all_weights.max())
        bins = np.arange(min_weight, max_weight + 0.5, 0.5)
        bin_centers = bins[:-1] + 0.25

        turkey_counts, _ = np.histogram(self.turkeys["weight"], bins=bins)
        order_counts, _ = np.histogram(self.orders["target_weight"], bins=bins)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

        ax1.plot(bin_centers, turkey_counts, marker='o', linestyle='-', color="orange", label="Turkeys")
        ax1.set_ylabel("Count")
        ax1.set_title("Turkey Weights Distribution")
        ax1.grid(axis='y', linestyle='--', alpha=0.7)
        ax1.legend()

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

    def print_tables(self):
        print("Orders:")
        print(self.orders, "\n")
        print("Turkeys:")
        print(self.turkeys, "\n")
