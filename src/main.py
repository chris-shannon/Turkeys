import flet as ft
from backend import Backend


def add_test_turkeys(backend):
    backend.add_turkey(1, 18)
    backend.add_turkey(2, 15)
    backend.add_turkey(3, 17)
    backend.add_turkey(4, 13)
    backend.add_turkey(5, 19)

def main(page: ft.Page):
    backend = Backend()

    # Turkey inputs
    tid_input = ft.TextField(label="Turkey ID", width=100)
    weight_input = ft.TextField(label="Weight", width=100)
    turkey_inputs = [tid_input, weight_input]

    # Order inputs
    oid_input = ft.TextField(label="Order ID", width=100)
    order_name_input = ft.TextField(label="Name", width=150)
    target_weight_input = ft.TextField(label="Target Weight", width=100)
    notes_input = ft.TextField(label="Notes", width=200)
    order_inputs = [oid_input, order_name_input, target_weight_input, notes_input]

    # Ham portion radio group
    ham_radio_group = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="None", label="None"),
            ft.Radio(value="Whole", label="Whole"),
            ft.Radio(value="1/2", label="1/2"),
            ft.Radio(value="1/4", label="1/4"),
        ]),
        value="None"
    )
    selected_turkey = None
    selected_order = None

    # ListViews
    turkey_lv = ft.ListView(expand=True, spacing=5, padding=10)
    order_lv = ft.ListView(expand=True, spacing=5, padding=10)

    # Refresh turkeys
    def refresh_turkeys():
        turkey_lv.controls.clear()
        for tid, turkey in backend.turkeys.to_dict("index").items():
            turkey_lv.controls.append(
                ft.ListTile(
                    title=ft.Text(f"TID: {tid}, Weight: {turkey['weight']}"),
                    data=tid,
                    selected=(tid == selected_turkey),  # highlight if selected
                    on_click=lambda e, tid=tid: select_turkey(tid)
                )
            )
        turkey_lv.update()

    # Refresh orders
    def refresh_orders():
        order_lv.controls.clear()
        for oid, order in backend.orders.to_dict("index").items():
            order_lv.controls.append(
                ft.ListTile(
                    title=ft.Text(f"OID: {oid}, Name: {order['name']}, Ham: {order['ham']}, Assigned Turkey: {order['assigned_weight']}"),
                    subtitle=ft.Text(f"Notes: {order['notes']}"),
                    data=oid,
                    selected=(oid == selected_order),  # highlight if selected
                    on_click=lambda e, oid=oid: select_order(oid)
                )
            )
        order_lv.update()

    def select_turkey(tid):
        nonlocal selected_turkey
        selected_turkey = tid
        refresh_turkeys()

    def select_order(oid):
        nonlocal selected_order
        selected_order = oid
        refresh_orders()

    def delete_selected_turkey(e):
        nonlocal selected_turkey
        if selected_turkey is not None:
            backend.remove_turkey(selected_turkey)
            selected_turkey = None
            refresh_turkeys()
            refresh_orders()

    def delete_selected_order(e):
        nonlocal selected_order
        if selected_order is not None:
            backend.remove_order(selected_order)
            selected_order = None
            refresh_orders()
            refresh_turkeys()

    def match_selected(e):
        if selected_order is None or selected_turkey is None:
            print("Select both an order and a turkey to match!")
            return
        try:
            backend.match(selected_order, selected_turkey)
        except ValueError as ve:
            print(ve)
        refresh_turkeys()
        refresh_orders()

    def auto_match(_):
        try:
            backend.auto_match()
        except ValueError as ve:
            print(ve)

        refresh_turkeys()
        refresh_orders()
    # Add turkey
    def add_turkey(e):
        try:
            tid = int(tid_input.value)
            weight = float(weight_input.value)
        except ValueError:
            print("Invalid turkey input!")
            return
        backend.add_turkey(tid, weight)
        tid_input.value = tid+1
        tid_input.update()
        weight_input.value = ""
        weight_input.focus()
        weight_input.update()
        refresh_turkeys()

    # Add order

    def add_order(e):
        try:
            oid = int(oid_input.value)
            target_weight = float(target_weight_input.value)
            name = order_name_input.value
            notes = notes_input.value
            ham = ham_radio_group.value
            order_inputs[0].focus()  # <--- HERE
            page.update()  # refresh the page to apply focus
        except ValueError:
            print("Invalid order input!")
            return

        backend.add_order(oid, target_weight, name, ham, notes)

        # Clear inputs
        oid_input.value = oid+1
        oid_input.update()
        target_weight_input.value = ""
        target_weight_input.update()
        order_name_input.value = ""
        order_name_input.update()
        notes_input.value = ""
        notes_input.update()
        ham_radio_group.value = "None"
        ham_radio_group.update()

        refresh_orders()

    def unmatch_turkey(e):
        tid = selected_turkey
        backend.remove_match_by_tid(tid)
        refresh_turkeys()
        refresh_orders()

    def unmatch_order(e):
        oid = selected_order
        backend.remove_match_by_tid(oid)
        refresh_turkeys()
        refresh_orders()

    # enter functionality for turkeys and orders
    for idx, field in enumerate(order_inputs):
        if idx < len(order_inputs) - 1:
            # move focus to next field
            field.on_submit = lambda e, i=idx: order_inputs[i + 1].focus()
        else:
            # last field triggers add_order
            field.on_submit = add_order
    for idx, field in enumerate(turkey_inputs):
        if idx < len(turkey_inputs) - 1:
            # Move focus to next field
            field.on_submit = lambda e, i=idx: turkey_inputs[i + 1].focus()
        else:
            # Last field triggers add_turkey
            field.on_submit = add_turkey
    # Layout
    page.add(
        ft.Row([
            # Turkeys column
            ft.Column([
                ft.Row([
                    tid_input,
                    weight_input,
                    ft.ElevatedButton("Add Turkey", on_click=add_turkey)
                ]),
                turkey_lv,  # ListView for turkeys
                ft.ElevatedButton("Delete Selected Turkey", on_click=delete_selected_turkey),# delete button
                ft.ElevatedButton("Unmatch Selected Turkey", on_click=unmatch_turkey)
            ], expand=True),

            # Orders column
            ft.Column([
                ft.Row([
                    oid_input,
                    order_name_input,
                    target_weight_input,
                    ft.ElevatedButton("Add Order", on_click=add_order)
                ]),
                ft.Row([ham_radio_group]),
                notes_input,
                order_lv,  # ListView for orders
                ft.ElevatedButton("Delete Selected Order", on_click=delete_selected_order),  # delete button
                ft.ElevatedButton("Unmatch Selected Order", on_click=unmatch_order),
                ft.ElevatedButton("Match Selected Order & Turkey", on_click=match_selected),
                ft.ElevatedButton("Automated Match", on_click=auto_match)
            ], expand=True),
        ], expand=True, spacing=20)
    )
ft.app(target=main)
