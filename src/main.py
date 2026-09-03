import flet as ft
import pandas as pd
import os
from backend import Backend


def main(page: ft.Page):
    page.title = "Turkey Manager"
    page.window_icon = "icon.png"
    backend = Backend()

    selected_turkey = None
    selected_order = None
    turkey_sort_col = "tid"
    turkey_sort_asc = True
    order_sort_col = "oid"
    order_sort_asc = True

    # --- Input fields ---
    tid_input = ft.TextField(label="Turkey ID", width=100)
    weight_input = ft.TextField(label="Weight", width=100)
    oid_input = ft.TextField(label="Order ID", width=100)
    order_name_input = ft.TextField(label="Name", width=150)
    target_weight_input = ft.TextField(label="Target Weight", width=100)
    notes_input = ft.TextField(label="Notes", width=200)
    ham_radio_group = ft.RadioGroup(
        content=ft.Row([
            ft.Text("Ham:", size=16),
            ft.Radio(value="None", label="None"),
            ft.Radio(value="Whole", label="Whole"),
            ft.Radio(value="1/2", label="1/2"),
            ft.Radio(value="1/4", label="1/4"),
        ]),
        value="None"
    )
    avg_disp_field = ft.TextField(label="Avg Displacement:", width=150, disabled=True, value="0.00")

    turkey_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("TID"), on_sort=lambda e: sort_turkeys("tid")),
            ft.DataColumn(ft.Text("Weight"), on_sort=lambda e: sort_turkeys("weight")),
            ft.DataColumn(ft.Text("Assigned")),
        ],
        rows=[]
    )
    order_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("OID"), on_sort=lambda e: sort_orders("oid")),
            ft.DataColumn(ft.Text("Name"), on_sort=lambda e: sort_orders("name")),
            ft.DataColumn(ft.Text("Target"), on_sort=lambda e: sort_orders("target_weight")),
            ft.DataColumn(ft.Text("Ham")),
            ft.DataColumn(ft.Text("Matched")),
            ft.DataColumn(ft.Text("Weight")),
            ft.DataColumn(ft.Text("Displacement"), on_sort=lambda e: sort_orders("displacement")),
            ft.DataColumn(ft.Text("Notes")),
        ],
        rows=[]
    )

    # --- Helpers ---
    def arrow(col, current_col, asc):
        if col == current_col:
            return "↑" if asc else "↓"
        return ""

    def select_turkey(tid):
        nonlocal selected_turkey
        selected_turkey = tid
        refresh_ui()

    def select_order(oid):
        nonlocal selected_order
        selected_order = oid
        refresh_ui()

    def sort_turkeys(col):
        nonlocal turkey_sort_col, turkey_sort_asc
        turkey_sort_asc = not turkey_sort_asc if turkey_sort_col == col else True
        turkey_sort_col = col
        refresh_ui()

    def sort_orders(col):
        nonlocal order_sort_col, order_sort_asc
        order_sort_asc = not order_sort_asc if order_sort_col == col else True
        order_sort_col = col
        refresh_ui()

    # --- Actions ---
    def add_turkey():
        try:
            tid = int(tid_input.value)
            weight = float(weight_input.value)
        except ValueError:
            return
        backend.add_turkey(tid, weight)
        tid_input.value = str(tid + 1)
        weight_input.value = ""
        tid_input.update()
        weight_input.update()
        weight_input.focus()
        refresh_ui()

    def add_order():
        try:
            oid = int(oid_input.value)
            target_weight = float(target_weight_input.value) if target_weight_input.value.strip() else 0
            name = order_name_input.value
            notes = notes_input.value
            ham = ham_radio_group.value
        except ValueError:
            return
        backend.add_order(oid, target_weight, name, ham, notes)
        oid_input.value = str(oid + 1)
        target_weight_input.value = ""
        order_name_input.value = ""
        notes_input.value = ""
        ham_radio_group.value = "None"
        oid_input.update()
        target_weight_input.update()
        order_name_input.update()
        notes_input.update()
        ham_radio_group.update()
        refresh_ui()

    def match_selected():
        if selected_order and selected_turkey:
            try:
                backend.match(selected_order, selected_turkey)
            except ValueError as ve:
                print(ve)
            refresh_ui()

    def delete_selected_turkey():
        nonlocal selected_turkey
        if selected_turkey is not None:
            backend.remove_turkey(selected_turkey)
            selected_turkey = None
            refresh_ui()

    def delete_selected_order():
        nonlocal selected_order
        if selected_order is not None:
            backend.remove_order(selected_order)
            selected_order = None
            refresh_ui()

    def match_closest():
        if selected_order is not None:
            try:
                backend.match_closest(selected_order)
            except ValueError as ve:
                print(ve)
            refresh_ui()

    def auto_match():
        try:
            backend.auto_match()
        except Exception as e:
            print(f"Auto match error: {e}")
        refresh_ui()

    # --- Refresh ---
    def refresh_ui():
        assigned = backend.orders.dropna(subset=["assigned_tid"])
        avg_disp = assigned["displacement"].abs().mean() if not assigned.empty else 0.0
        avg_disp_field.value = f"{avg_disp:.2f}"
        avg_disp_field.update()

        df_turkeys = backend.turkeys.sort_values(turkey_sort_col, ascending=turkey_sort_asc)
        turkey_table.rows.clear()
        for tid, t in df_turkeys.to_dict("index").items():
            if t["assigned"]:
                match = backend.orders[backend.orders["assigned_tid"] == tid]
                assigned_text = match.iloc[0]["name"] if not match.empty else "Yes"
                assigned_color = ft.Colors.GREEN
            else:
                assigned_text = "No"
                assigned_color = ft.Colors.RED
            turkey_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(tid))),
                        ft.DataCell(ft.Text(str(t["weight"]))),
                        ft.DataCell(ft.Text(assigned_text, color=assigned_color)),
                    ],
                    selected=(tid == selected_turkey),
                    on_select_changed=lambda e, tid=tid: select_turkey(tid),
                )
            )
        turkey_table.columns = [
            ft.DataColumn(ft.Text(f"TID {arrow('tid', turkey_sort_col, turkey_sort_asc)}"), on_sort=lambda e: sort_turkeys("tid")),
            ft.DataColumn(ft.Text(f"Weight {arrow('weight', turkey_sort_col, turkey_sort_asc)}"), on_sort=lambda e: sort_turkeys("weight")),
            ft.DataColumn(ft.Text("Assigned")),
        ]
        turkey_table.update()

        df_orders = backend.orders.sort_values(order_sort_col, ascending=order_sort_asc)
        order_table.rows.clear()
        for oid, o in df_orders.to_dict("index").items():
            assigned_tid = str(o["assigned_tid"]) if pd.notna(o["assigned_tid"]) else "No"
            assigned_tid_color = ft.Colors.GREEN if pd.notna(o["assigned_tid"]) else ft.Colors.RED
            assigned_weight = str(o["assigned_weight"]) if pd.notna(o["assigned_weight"]) else "No"
            assigned_weight_color = ft.Colors.GREEN if pd.notna(o["assigned_weight"]) else ft.Colors.RED

            if pd.notna(o["displacement"]):
                disp = o["displacement"]
                disp_text = f"{disp:+.1f}"
                disp_color = ft.Colors.GREEN if abs(disp) <= 0.5 else ft.Colors.YELLOW if abs(disp) <= 1.0 else ft.Colors.RED
            else:
                disp_text = "—"
                disp_color = ft.Colors.GREY

            order_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(oid))),
                        ft.DataCell(ft.Text(o["name"])),
                        ft.DataCell(ft.Text(str(o["target_weight"]))),
                        ft.DataCell(ft.Text(o["ham"])),
                        ft.DataCell(ft.Text(assigned_tid, color=assigned_tid_color)),
                        ft.DataCell(ft.Text(assigned_weight, color=assigned_weight_color)),
                        ft.DataCell(ft.Text(disp_text, color=disp_color)),
                        ft.DataCell(ft.Text(o["notes"])),
                    ],
                    selected=(oid == selected_order),
                    on_select_changed=lambda e, oid=oid: select_order(oid),
                )
            )
        order_table.columns = [
            ft.DataColumn(ft.Text(f"OID {arrow('oid', order_sort_col, order_sort_asc)}"), on_sort=lambda e: sort_orders("oid")),
            ft.DataColumn(ft.Text(f"Name {arrow('name', order_sort_col, order_sort_asc)}"), on_sort=lambda e: sort_orders("name")),
            ft.DataColumn(ft.Text(f"Target {arrow('target_weight', order_sort_col, order_sort_asc)}"), on_sort=lambda e: sort_orders("target_weight")),
            ft.DataColumn(ft.Text("Ham")),
            ft.DataColumn(ft.Text("Matched")),
            ft.DataColumn(ft.Text("Weight")),
            ft.DataColumn(ft.Text(f"Displacement {arrow('displacement', order_sort_col, order_sort_asc)}"), on_sort=lambda e: sort_orders("displacement")),
            ft.DataColumn(ft.Text("Notes")),
        ]
        order_table.update()

    # --- Enter key navigation ---
    tid_input.on_submit = lambda e: weight_input.focus()
    weight_input.on_submit = lambda e: add_turkey()
    oid_input.on_submit = lambda e: order_name_input.focus()
    order_name_input.on_submit = lambda e: target_weight_input.focus()
    target_weight_input.on_submit = lambda e: notes_input.focus()
    notes_input.on_submit = lambda e: add_order()

    # --- Save/Load dialogs ---
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    save_name_input = ft.TextField(label="File name", value="save", width=200)

    def do_save(e):
        name = save_name_input.value.strip() or "save"
        path = os.path.join(data_dir, name if name.endswith(".pkl") else name + ".pkl")
        backend.save(path)
        save_dialog.open = False
        page.update()

    def do_load(filename):
        backend.load(os.path.join(data_dir, filename))
        load_dialog.open = False
        refresh_ui()

    def build_load_dialog():
        files = [f for f in os.listdir(data_dir) if f.endswith(".pkl")] if os.path.exists(data_dir) else []
        load_dialog.content = ft.Column(
            [ft.TextButton(f, on_click=lambda e, f=f: do_load(f)) for f in files] or [ft.Text("No saves found.")],
            tight=True,
        )

    save_dialog = ft.AlertDialog(
        title=ft.Text("Save"),
        content=ft.Column([save_name_input], tight=True),
        actions=[
            ft.TextButton("Save", on_click=do_save),
            ft.TextButton("Cancel", on_click=lambda e: setattr(save_dialog, "open", False) or page.update()),
        ],
    )

    load_dialog = ft.AlertDialog(
        title=ft.Text("Load"),
        content=ft.Text(""),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: setattr(load_dialog, "open", False) or page.update()),
        ],
    )

    def open_save_dialog(e):
        page.overlay.append(save_dialog)
        save_dialog.open = True
        page.update()

    def open_load_dialog(e):
        build_load_dialog()
        page.overlay.append(load_dialog)
        load_dialog.open = True
        page.update()

    # --- Buttons ---
    add_turkey_btn = ft.ElevatedButton("Add Turkey", on_click=lambda e: add_turkey())
    delete_turkey_btn = ft.ElevatedButton("Delete Selected Turkey", on_click=lambda e: delete_selected_turkey())
    add_order_btn = ft.ElevatedButton("Add Order", on_click=lambda e: add_order())
    delete_order_btn = ft.ElevatedButton("Delete Selected Order", on_click=lambda e: delete_selected_order())
    match_btn = ft.ElevatedButton("Match Selected", on_click=lambda e: match_selected())
    match_closest_btn = ft.ElevatedButton("Find Closest Turkey", on_click=lambda e: match_closest())
    auto_match_btn = ft.ElevatedButton("Auto Match", on_click=lambda e: auto_match())
    unmatch_turkey_btn = ft.ElevatedButton("Unmatch Selected Turkey", on_click=lambda e: (backend.remove_match_by_tid(selected_turkey), refresh_ui()) if selected_turkey else None)
    unmatch_order_btn = ft.ElevatedButton("Unmatch Selected Order", on_click=lambda e: (backend.remove_match_by_oid(selected_order), refresh_ui()) if selected_order else None)
    make_pdfs_btn = ft.ElevatedButton("Generate PDFs", on_click=lambda e: (backend.export_turkey_orders_pdf(), backend.export_ham_orders_without_turkey(), backend.export_free_turkeys_pdf()))
    save_btn = ft.ElevatedButton("Save", on_click=open_save_dialog)
    load_btn = ft.ElevatedButton("Load", on_click=open_load_dialog)

    page.add(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Row([tid_input, weight_input], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Row([add_turkey_btn, delete_turkey_btn], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(
                            content=ft.Column([turkey_table], expand=True, scroll=ft.ScrollMode.AUTO),
                            expand=True, padding=5,
                        ),
                    ],
                    expand=False, spacing=10,
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    [
                        match_btn, match_closest_btn, auto_match_btn,
                        ft.Container(height=20),
                        unmatch_turkey_btn, unmatch_order_btn,
                        ft.Container(height=40),
                        make_pdfs_btn, save_btn, load_btn, avg_disp_field,
                    ],
                    expand=False, spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Row([oid_input, order_name_input, target_weight_input], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Row([notes_input, ham_radio_group], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Row([add_order_btn, delete_order_btn], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(
                            content=ft.Column([order_table], expand=True, scroll=ft.ScrollMode.AUTO),
                            expand=True, padding=5,
                        ),
                    ],
                    expand=True, spacing=10,
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            expand=True, spacing=20,
        ),
    )
    refresh_ui()


ft.app(target=main)
