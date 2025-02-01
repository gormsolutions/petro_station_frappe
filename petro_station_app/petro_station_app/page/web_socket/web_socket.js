frappe.pages['web-socket'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Web Socket Page',
        single_column: true
    });

    // Create a section to display item data
    var itemDataDiv = $('<div>').appendTo(page.main);
    itemDataDiv.html('<h3>Items</h3><div id="item_list">Loading items...</div>');
    
    // Create a button for creating an item
    var buttonsDiv = $('<div>').appendTo(page.main);
    buttonsDiv.html('<button id="create_item_button">Create Item</button>');
    
    // Create item on button click
    $('#create_item_button').on('click', function() {
        createItem();
    });

    // Function to create an item
    function createItem() {
        let item_data = {
            item_code: 'Gorm Racheal',
            item_name: 'ooo786',
            item_group: 'Oils',
            stock_uom: 'Nos'
            // add other fields here as necessary
        };

        frappe.call({
            method: 'frappe.desk.doctype.item.item.create_item',
            args: {
                item_data: JSON.stringify(item_data)
            },
            callback: function(response) {
                if (response.message.status === 'success') {
                    console.log('Item created:', response.message.item_code);
                    alert('Item created successfully: ' + response.message.item_code);

                    // After item creation, re-fetch the updated list
                    fetchItems();
                } else {
                    console.log('Error:', response.message.message);
                    alert('Error creating item: ' + response.message.message);
                }
            }
        });
    }

    // Function to fetch items initially
    function fetchItems() {
        frappe.call({
            method: 'gormsolutions_mobile_app.custom_api.web_socket.item.fetch_items',
            callback: function(response) {
                if (response.message.status === 'success') {
                    console.log('Items fetched:', response.message.data);
                    // Display the fetched items in the item list
                    updateItemList(response.message.data);
                } else {
                    console.log('Error:', response.message.message);
                    $('#item_list').html('Error fetching items: ' + response.message.message);
                }
            }
        });
    }

    // Function to update the item list on the page
    function updateItemList(items) {
        $('#item_list').html('<ul>' + items.map(function(item) {
            return '<li>' + item.item_code + ' - ' + item.item_name + '</li>';
        }).join('') + '</ul>');
    }

    // Listen for real-time updates (WebSocket)
    frappe.realtime.on('item_data_update', function(data) {
        console.log('Real-time update received:', data.items);
        // Update the UI with the new items
        updateItemList(data.items);
    });

    // Listen for real-time errors
    frappe.realtime.on('item_data_error', function(data) {
        console.log('Error:', data.error);
        $('#item_list').html('Error: ' + data.error);
    });

    // Automatically fetch the items when the page is loaded
    fetchItems();
}
