// ============================================================
// EASY SALES - MAIN JAVASCRIPT
// ============================================================


// ============================================================
// 1. CART
// ============================================================

let cart = [];


// ============================================================
// 2. PAYMENT METHOD
// ============================================================

let selectedPaymentMethod = "cash";


// ============================================================
// 3. PAGE START
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        loadProducts();

        setupButtons();

    }
);


// ============================================================
// 4. LOAD PRODUCTS
// ============================================================

async function loadProducts() {

    try {

        const response = await fetch(
            "/api/products?t=" + Date.now()
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            console.error(
                "Could not load products:",
                data.message
            );

            return;

        }

        displayProducts(
            data.products
        );

    } catch (error) {

        console.error(
            "PRODUCT LOAD ERROR:",
            error
        );

    }

}


// ============================================================
// 5. DISPLAY PRODUCTS
// ============================================================

function displayProducts(products) {

    const productArea =
        document.getElementById(
            "product-area"
        );

    if (!productArea) {
        return;
    }

    productArea.innerHTML = "";

    if (!products || products.length === 0) {

        productArea.innerHTML = `
            <p class="empty-products">
                No products available.
            </p>
        `;

        return;
    }

    products.forEach(function(product) {

        const row =
            document.createElement("div");

        row.className =
            "product-row";

        row.dataset.id =
            product.id;

        row.innerHTML = `

            <div class="product-information">

                <strong>
                    ${escapeHtml(product.name)}
                </strong>

                <span>
                    Stock: ${product.stock}
                </span>

            </div>

            <div class="product-price">
                R${Number(product.price).toFixed(2)}
            </div>

            <button
                class="edit-product-button"
                type="button">

                EDIT

            </button>

            <button
                class="add-button"
                type="button">

                +

            </button>
        `;

        productArea.appendChild(row);

        const button =
            row.querySelector(".add-button");

        button.addEventListener(
            "click",
            function() {

                addToCart(product);

            }
        );

        const editButton =
            row.querySelector(
                ".edit-product-button"
            );

        if (editButton) {

            editButton.addEventListener(
                "click",
                function() {

                    openEditProduct(product);

                }
            );

        }

    });

}


// ============================================================
// 6. ADD TO CART
// ============================================================

function addToCart(product) {

    const stock =
        Number(product.stock);

    if (stock <= 0) {

        showMessage(
            "This product is out of stock."
        );

        return;
    }

    const existingProduct =
        cart.find(function(item) {

            return Number(item.id) ===
                   Number(product.id);

        });

    if (existingProduct) {

        if (
            existingProduct.quantity >=
            stock
        ) {

            showMessage(
                "No more stock available."
            );

            return;
        }

        existingProduct.quantity++;

    } else {

        cart.push({

            id: product.id,

            name: product.name,

            price: Number(product.price),

            stock: stock,

            quantity: 1

        });

    }

    updateCart();

}


// ============================================================
// 7. UPDATE CART
// ============================================================

function updateCart() {

    let totalItems = 0;

    cart.forEach(function(product) {

        totalItems +=
            product.quantity;

    });

    const counter =
        document.getElementById(
            "cart-count"
        );

    if (counter) {

        counter.textContent =
            totalItems;

    }

    displayCart();

}


// ============================================================
// 8. DISPLAY CART
// ============================================================

function displayCart() {

    const container =
        document.getElementById(
            "cart-items"
        );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (cart.length === 0) {

        container.innerHTML = `

            <p class="empty-cart">
                Your cart is empty.
            </p>

        `;

        updateCartTotal();

        return;
    }

    cart.forEach(function(product, index) {

        const item =
            document.createElement("div");

        item.className =
            "cart-item";

        const itemTotal =
            product.price *
            product.quantity;

        item.innerHTML = `

            <div class="cart-item-info">

                <strong>
                    ${escapeHtml(product.name)}
                </strong>

                <span>
                    R${product.price.toFixed(2)} each
                </span>

            </div>

            <div class="quantity-controls">

                <button
                    type="button"
                    data-action="decrease">
                    -
                </button>

                <span>
                    ${product.quantity}
                </span>

                <button
                    type="button"
                    data-action="increase">
                    +
                </button>

            </div>

            <strong class="cart-item-total">
                R${itemTotal.toFixed(2)}
            </strong>

        `;

        container.appendChild(item);

        item.querySelector(
            '[data-action="decrease"]'
        ).addEventListener(
            "click",
            function() {

                decreaseQuantity(index);

            }
        );

        item.querySelector(
            '[data-action="increase"]'
        ).addEventListener(
            "click",
            function() {

                increaseQuantity(index);

            }
        );

    });

    updateCartTotal();

}


// ============================================================
// 9. INCREASE QUANTITY
// ============================================================

function increaseQuantity(index) {

    if (!cart[index]) {
        return;
    }

    const product =
        cart[index];

    if (
        product.quantity >=
        product.stock
    ) {

        showMessage(
            "No more stock available."
        );

        return;
    }

    product.quantity++;

    updateCart();

}


// ============================================================
// 10. DECREASE QUANTITY
// ============================================================

function decreaseQuantity(index) {

    if (!cart[index]) {
        return;
    }

    cart[index].quantity--;

    if (
        cart[index].quantity <= 0
    ) {

        cart.splice(
            index,
            1
        );

    }

    updateCart();

}


// ============================================================
// 11. CART TOTAL
// ============================================================

function getCartTotal() {

    let total = 0;

    cart.forEach(function(product) {

        total +=
            product.price *
            product.quantity;

    });

    return total;

}


function updateCartTotal() {

    const totalElement =
        document.getElementById(
            "cart-total"
        );

    if (totalElement) {

        totalElement.textContent =
            "R" +
            getCartTotal().toFixed(2);

    }

}


// ============================================================
// 12. BUTTON SETUP
// ============================================================

function setupButtons() {

    const cartButton =
        document.getElementById(
            "cart-button"
        );

    if (cartButton) {

        cartButton.addEventListener(
            "click",
            openCart
        );

    }


    const closeCartButton =
        document.getElementById(
            "close-cart"
        );

    if (closeCartButton) {

        closeCartButton.addEventListener(
            "click",
            closeCart
        );

    }


    const clearCartButton =
        document.getElementById(
            "clear-cart"
        );

    if (clearCartButton) {

        clearCartButton.addEventListener(
            "click",
            clearCart
        );

    }


    const addProductButton =
        document.getElementById(
            "add-product-button"
        );

    if (addProductButton) {

        addProductButton.addEventListener(
            "click",
            openAddProduct
        );

    }


    const closeAddProductButton =
        document.getElementById(
            "close-add-product"
        );

    if (closeAddProductButton) {

        closeAddProductButton.addEventListener(
            "click",
            closeAddProduct
        );

    }


    const saveProductButton =
        document.getElementById(
            "save-product"
        );

    if (saveProductButton) {

        saveProductButton.addEventListener(
            "click",
            saveProduct
        );

    }


    const closeEditProductButton =
        document.getElementById(
            "close-edit-product"
        );

    if (closeEditProductButton) {

        closeEditProductButton.addEventListener(
            "click",
            closeEditProduct
        );

    }


    const saveEditProductButton =
        document.getElementById(
            "save-edit-product"
        );

    if (saveEditProductButton) {

        saveEditProductButton.addEventListener(
            "click",
            saveEditedProduct
        );

    }


    // ========================================================
    // STOCK TAKE
    // ========================================================

    const stockTakeButton =
        document.getElementById(
            "stock-take-button"
        );

    if (stockTakeButton) {

        stockTakeButton.addEventListener(
            "click",
            openStockTake
        );

    }


    const closeStockTakeButton =
        document.getElementById(
            "close-stock-take"
        );

    if (closeStockTakeButton) {

        closeStockTakeButton.addEventListener(
            "click",
            closeStockTake
        );

    }


    const checkoutButton =
        document.getElementById(
            "checkout-button"
        );

    if (checkoutButton) {

        checkoutButton.addEventListener(
            "click",
            openCheckout
        );

    }


    const closeCheckoutButton =
        document.getElementById(
            "close-checkout"
        );

    if (closeCheckoutButton) {

        closeCheckoutButton.addEventListener(
            "click",
            closeCheckout
        );

    }


    const cashButton =
        document.getElementById(
            "cash-payment"
        );

    if (cashButton) {

        cashButton.addEventListener(
            "click",
            selectCashPayment
        );

    }


    const cardButton =
        document.getElementById(
            "card-payment"
        );

    if (cardButton) {

        cardButton.addEventListener(
            "click",
            selectCardPayment
        );

    }


    const cashReceived =
        document.getElementById(
            "cash-received"
        );

    if (cashReceived) {

        cashReceived.addEventListener(
            "input",
            calculateChange
        );

    }


    const saleFeeInput =
        document.getElementById(
            "sale-fee"
        );

    if (saleFeeInput) {

        saleFeeInput.addEventListener(
            "input",
            updateCheckoutTotals
        );

    }


    const completeSaleButton =
        document.getElementById(
            "complete-sale"
        );

    if (completeSaleButton) {

        completeSaleButton.addEventListener(
            "click",
            completeSale
        );

    }


    setupProductSearch();

}


// ============================================================
// 13. CART WINDOW
// ============================================================

function openCart() {

    const element =
        document.getElementById(
            "cart-window"
        );

    if (element) {

        element.classList.add("show");

    }

}


function closeCart() {

    const element =
        document.getElementById(
            "cart-window"
        );

    if (element) {

        element.classList.remove("show");

    }

}


function clearCart() {

    cart = [];

    updateCart();

    closeCart();

    const checkout =
        document.getElementById(
            "checkout-window"
        );

    if (checkout) {

        checkout.classList.remove("show");

    }

}


// ============================================================
// 14. ADD PRODUCT
// ============================================================

function openAddProduct() {

    const element =
        document.getElementById(
            "add-product-window"
        );

    if (element) {

        element.classList.add("show");

    }

}


function closeAddProduct() {

    const element =
        document.getElementById(
            "add-product-window"
        );

    if (element) {

        element.classList.remove("show");

    }

}


// ============================================================
// 15. SAVE PRODUCT
// ============================================================

async function saveProduct() {

    const nameInput =
        document.getElementById(
            "product-name"
        );

    const priceInput =
        document.getElementById(
            "product-price"
        );

    const stockInput =
        document.getElementById(
            "product-stock"
        );

    const saveButton =
        document.getElementById(
            "save-product"
        );

    if (
        !nameInput ||
        !priceInput ||
        !stockInput ||
        !saveButton
    ) {
        return;
    }

    const name =
        nameInput.value.trim();

    const price =
        parseFloat(priceInput.value);

    const stock =
        parseInt(
            stockInput.value,
            10
        );


    if (!name) {

        showAddProductMessage(
            "Enter a product name."
        );

        return;
    }


    if (
        isNaN(price) ||
        price < 0
    ) {

        showAddProductMessage(
            "Enter a valid price."
        );

        return;
    }


    if (
        isNaN(stock) ||
        stock < 0
    ) {

        showAddProductMessage(
            "Enter a valid stock quantity."
        );

        return;
    }


    saveButton.disabled = true;

    saveButton.textContent =
        "SAVING...";


    try {

        const response =
            await fetch(
                "/api/products",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        name: name,

                        price: price,

                        stock: stock

                    })

                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            showAddProductMessage(

                data.message ||
                "Could not save product."

            );

            return;
        }


        showAddProductMessage(
            "Product saved successfully."
        );


        nameInput.value = "";

        priceInput.value = "";

        stockInput.value = "";


        await loadProducts();


        setTimeout(
            function() {

                closeAddProduct();

            },
            500
        );


    } catch (error) {

        console.error(
            "SAVE PRODUCT ERROR:",
            error
        );

        showAddProductMessage(
            "Could not connect to Easy Sales."
        );


    } finally {

        saveButton.disabled = false;

        saveButton.textContent =
            "SAVE PRODUCT";

    }

}


// ============================================================
// 16. OPEN STOCK TAKE
// ============================================================

function openStockTake() {

    const windowElement =
        document.getElementById(
            "stock-take-window"
        );

    if (!windowElement) {

        console.error(
            "Stock Take window not found."
        );

        return;
    }


    windowElement.classList.add(
        "show"
    );


    loadStockTake();

}


// ============================================================
// 17. CLOSE STOCK TAKE
// ============================================================

function closeStockTake() {

    const windowElement =
        document.getElementById(
            "stock-take-window"
        );

    if (windowElement) {

        windowElement.classList.remove(
            "show"
        );

    }

}


// ============================================================
// 18. LOAD STOCK TAKE
// ============================================================

async function loadStockTake() {

    const list =
        document.getElementById(
            "stock-take-list"
        );

    if (!list) {
        return;
    }


    list.innerHTML = `

        <p>
            Loading stock...
        </p>

    `;


    try {

        const response =
            await fetch(
                "/api/stock-take?t=" +
                Date.now()
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            list.innerHTML = `

                <p>
                    ${escapeHtml(
                        data.message ||
                        "Could not load stock."
                    )}
                </p>

            `;

            return;
        }


        if (
            !data.products ||
            data.products.length === 0
        ) {

            list.innerHTML = `

                <p>
                    No products found.
                </p>

            `;

            return;
        }


        list.innerHTML = "";


        data.products.forEach(
            function(product) {

                createStockCard(
                    product,
                    list
                );

            }
        );


    } catch (error) {

        console.error(
            "STOCK TAKE ERROR:",
            error
        );


        list.innerHTML = `

            <p>
                Could not connect to Easy Sales.
            </p>

        `;

    }

}


// ============================================================
// 19. STOCK CONTROL REPORTS
// ============================================================


// ============================================================
// OPEN STOCK CONTROL
// ============================================================

function openStockTake() {

    const stockWindow =
        document.getElementById(
            "stock-take-window"
        );

    if (!stockWindow) {

        console.error(
            "Stock Control window not found."
        );

        return;

    }

    stockWindow.classList.add(
        "show"
    );

    showCurrentStockReport();

}


// ============================================================
// CLOSE STOCK CONTROL
// ============================================================

function closeStockTake() {

    const stockWindow =
        document.getElementById(
            "stock-take-window"
        );

    if (stockWindow) {

        stockWindow.classList.remove(
            "show"
        );

    }

}
// --------------------------------------------------------
// STOCK CONTROL REPORT TABS
// --------------------------------------------------------

const currentStockTab =
    document.getElementById(
        "current-stock-tab"
    );

if (currentStockTab) {

    currentStockTab.addEventListener(
        "click",
        showCurrentStockReport
    );

}


const movementHistoryTab =
    document.getElementById(
        "movement-history-tab"
    );

if (movementHistoryTab) {

    movementHistoryTab.addEventListener(
        "click",
        showMovementHistory
    );

}


const stocktakeHistoryTab =
    document.getElementById(
        "stocktake-history-tab"
    );

if (stocktakeHistoryTab) {

    stocktakeHistoryTab.addEventListener(
        "click",
        showStocktakeHistory
    );

}


// ============================================================
// SET ACTIVE TAB
// ============================================================

function setStockTab(
    activeTab
) {

    document
        .querySelectorAll(
            ".stock-tab"
        )
        .forEach(
            function(tab) {

                tab.classList.remove(
                    "active"
                );

            }
        );


    if (activeTab) {

        activeTab.classList.add(
            "active"
        );

    }

}


// ============================================================
// CURRENT STOCK REPORT
// ============================================================

async function showCurrentStockReport() {

    const content =
        document.getElementById(
            "stock-report-content"
        );

    const tab =
        document.getElementById(
            "current-stock-tab"
        );


    if (!content) {

        return;

    }


    setStockTab(
        tab
    );


    content.innerHTML = `

        <div class="report-heading">

            <h3>
                Current Stock
            </h3>

            <p>
                Current inventory position
            </p>

        </div>


        <p class="report-loading">

            Loading current stock...

        </p>

    `;


    try {

        const response =
            await fetch(
                "/api/stock-take?t=" +
                Date.now()
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Could not load stock."
            );

        }


        let html = `

            <div class="report-heading">

                <h3>
                    Current Stock
                </h3>

                <p>
                    Current inventory position
                </p>

            </div>

        `;


        if (
            !data.products ||
            data.products.length === 0
        ) {

            html += `

                <div class="report-empty">

                    No products found.

                </div>

            `;

        } else {

            data.products.forEach(
                function(product) {

                    html += `

                        <div class="stock-report-card">

                            <div class="stock-report-title">

                                <div>

                                    <strong>

                                        ${escapeHtml(
                                            product.name
                                        )}

                                    </strong>

                                    <span>

                                        Selling Price:
                                        R${Number(
                                            product.price
                                        ).toFixed(2)}

                                    </span>

                                </div>

                            </div>


                            <div class="stock-report-divider">
                            </div>


                            <div class="stock-report-grid">


                                <div class="report-stat">

                                    <span>
                                        SYSTEM STOCK
                                    </span>

                                    <strong>
                                        ${product.stock}
                                    </strong>

                                </div>


                                <div class="report-stat">

                                    <span>
                                        SOLD TODAY
                                    </span>

                                    <strong>
                                        ${product.sold_today}
                                    </strong>

                                </div>


                                <div class="report-stat">

                                    <span>
                                        SALES TODAY
                                    </span>

                                    <strong>

                                        R${Number(
                                            product.sales_today
                                        ).toFixed(2)}

                                    </strong>

                                </div>

                            </div>

                        </div>

                    `;

                }
            );

        }


        content.innerHTML =
            html;


    } catch (error) {

        console.error(
            "CURRENT STOCK REPORT ERROR:",
            error
        );


        content.innerHTML = `

            <div class="report-error">

                Could not load current stock report.

            </div>

        `;

    }

}


// ============================================================
// MOVEMENT HISTORY REPORT
// ============================================================

async function showMovementHistory() {

    const content =
        document.getElementById(
            "stock-report-content"
        );

    const tab =
        document.getElementById(
            "movement-history-tab"
        );


    if (!content) {

        return;

    }


    setStockTab(
        tab
    );


    content.innerHTML = `

        <div class="report-heading">

            <h3>
                Movement History
            </h3>

            <p>
                Complete record of stock movements
            </p>

        </div>

        <p class="report-loading">
            Loading movement history...
        </p>

    `;


    try {

        const response =
            await fetch(
                "/api/stock-movements?t=" +
                Date.now()
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Could not load movement history."
            );

        }


        let html = `

            <div class="report-heading">

                <h3>
                    Movement History
                </h3>

                <p>
                    Complete record of stock movements
                </p>

            </div>

        `;


        if (
            !data.movements ||
            data.movements.length === 0
        ) {

            html += `

                <div class="report-empty">

                    No stock movements recorded yet.

                </div>

            `;

        } else {

            data.movements.forEach(
                function(movement) {

                    const adjustment =
                        Number(
                            movement.adjustment
                        );


                    let adjustmentText =
                        adjustment > 0
                            ? "+" + adjustment
                            : adjustment;


                    html += `

                        <div class="movement-card">

                            <div class="movement-top">

                                <strong>

                                    ${escapeHtml(
                                        movement.product_name
                                    )}

                                </strong>

                                <span>

                                    ${escapeHtml(
                                        movement.created_at
                                    )}

                                </span>

                            </div>


                            <div class="movement-type">

                                ${escapeHtml(
                                    movement.movement_type
                                )}

                            </div>


                            <div class="movement-grid">


                                <div>

                                    <span>
                                        BEFORE
                                    </span>

                                    <strong>
                                        ${movement.stock_before}
                                    </strong>

                                </div>


                                <div>

                                    <span>
                                        ADDED
                                    </span>

                                    <strong>
                                        ${movement.quantity_added}
                                    </strong>

                                </div>


                                <div>

                                    <span>
                                        SOLD
                                    </span>

                                    <strong>
                                        ${movement.quantity_sold}
                                    </strong>

                                </div>


                                <div>

                                    <span>
                                        ADJUSTMENT
                                    </span>

                                    <strong>
                                        ${adjustmentText}
                                    </strong>

                                </div>


                                <div>

                                    <span>
                                        AFTER
                                    </span>

                                    <strong>
                                        ${movement.stock_after}
                                    </strong>

                                </div>

                            </div>


                            <div class="movement-reason">

                                <span>
                                    Reason
                                </span>

                                <p>

                                    ${escapeHtml(
                                        movement.reason ||
                                        "No reason recorded."
                                    )}

                                </p>

                            </div>

                        </div>

                    `;

                }
            );

        }


        content.innerHTML =
            html;


    } catch (error) {

        console.error(
            "MOVEMENT HISTORY ERROR:",
            error
        );


        content.innerHTML = `

            <div class="report-error">

                Could not load movement history.

            </div>

        `;

    }

}


// ============================================================
// STOCKTAKE HISTORY / MONTHLY REPORTS
// ============================================================

async function showStocktakeHistory() {

    const content =
        document.getElementById(
            "stock-report-content"
        );

    const tab =
        document.getElementById(
            "stocktake-history-tab"
        );

    if (!content) {
        return;
    }

    setStockTab(tab);

    content.innerHTML = `

        <div class="report-heading">

            <h3>
                Monthly Stock Report
            </h3>

            <p>
                Reconcile cash, card sales, stock and damaged goods.
            </p>

        </div>

        <div
            id="monthly-sales-summary"
            class="monthly-sales-summary">

            <div class="report-loading">
                Calculating current month sales...
            </div>

        </div>

        <div class="monthly-report-form">

            <label for="cash-at-hand">
                Cash at Hand
            </label>

            <input
                id="cash-at-hand"
                class="monthly-report-input"
                type="number"
                min="0"
                step="0.01"
                placeholder="Enter physical cash in register">

            <button
                id="damaged-goods-button"
                class="monthly-report-save-button"
                type="button">

                DAMAGED GOODS

            </button>

            <div
                id="damaged-goods-summary"
                class="monthly-report-status">
                No damaged goods selected.
            </div>

            <button
                id="save-monthly-report"
                class="monthly-report-save-button"
                type="button">

                GENERATE MONTHLY REPORT

            </button>

            <div
                id="monthly-report-status"
                class="monthly-report-status">

            </div>

        </div>

        <div class="report-heading monthly-history-heading">

            <h3>
                Report History
            </h3>

            <p>
                Previous stock and sales reconciliations.
            </p>

        </div>

        <p class="report-loading">
            Loading saved reports...
        </p>

    `;

    const damagedGoodsButton =
        document.getElementById(
            "damaged-goods-button"
        );

    if (damagedGoodsButton) {

        damagedGoodsButton.addEventListener(
            "click",
            openDamagedGoodsPopup
        );

    }

    const saveButton =
        document.getElementById(
            "save-monthly-report"
        );

    if (saveButton) {

        saveButton.addEventListener(
            "click",
            saveMonthlyReport
        );

    }

    await loadMonthlySalesSummary();
    await loadMonthlyReports();

}


// ============================================================
// LOAD CURRENT MONTH SALES SUMMARY
// ============================================================

async function loadMonthlySalesSummary() {

    const container =
        document.getElementById(
            "monthly-sales-summary"
        );

    if (!container) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/monthly-sales-summary?t=" +
                Date.now()
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {
            throw new Error(
                data.message ||
                "Could not calculate sales summary."
            );
        }

        const summary =
            data.summary || {};

        container.innerHTML = `

            <div class="report-heading">
                <h3>
                    Sales Reconciliation
                </h3>

                <p>
                    Recorded sales for ${escapeHtml(
                        summary.report_month || ""
                    )}
                </p>
            </div>

            <div class="monthly-report-grid">

                <div class="report-stat">
                    <span>CASH SALES</span>
                    <strong>
                        ${summary.cash_sales_count || 0}
                        &nbsp;—&nbsp;
                        R${Number(
                            summary.cash_sales_amount || 0
                        ).toFixed(2)}
                    </strong>
                </div>

                <div class="report-stat">
                    <span>CARD SALES</span>
                    <strong>
                        ${summary.card_sales_count || 0}
                        &nbsp;—&nbsp;
                        R${Number(
                            summary.card_sales_amount || 0
                        ).toFixed(2)}
                    </strong>
                </div>

                <div class="report-stat">
                    <span>TOTAL SALES</span>
                    <strong>
                        ${summary.total_sales_count || 0}
                        &nbsp;—&nbsp;
                        R${Number(
                            summary.total_sales_amount || 0
                        ).toFixed(2)}
                    </strong>
                </div>

                <div class="report-stat">
                    <span>UNITS SOLD</span>
                    <strong>
                        ${summary.total_sales_units || 0}
                    </strong>
                </div>

                <div class="report-stat">
                    <span>EXPECTED CASH</span>
                    <strong>
                        R${Number(
                            summary.cash_sales_amount || 0
                        ).toFixed(2)}
                    </strong>
                </div>

            </div>

        `;

    } catch (error) {

        console.error(
            "MONTHLY SALES SUMMARY ERROR:",
            error
        );

        container.innerHTML = `

            <div class="report-error">
                Could not calculate current month sales.
            </div>

        `;

    }

}


// ============================================================
// SAVE MONTHLY REPORT
// ============================================================

async function saveMonthlyReport() {

    const cashInput =
        document.getElementById(
            "cash-at-hand"
        );

    const button =
        document.getElementById(
            "save-monthly-report"
        );

    if (!cashInput || !button) {
        return;
    }

    const cashAtHand =
        parseFloat(cashInput.value);

    if (isNaN(cashAtHand) || cashAtHand < 0) {

        showMonthlyReportStatus(
            "Enter a valid cash amount."
        );

        return;
    }

    button.disabled = true;
    button.textContent = "SAVING...";

    try {

        const response =
            await fetch(
                "/api/monthly-reports",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        cash_at_hand:
                            cashAtHand,
                        damaged_goods:
                            damagedGoodsSelection
                    })
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {
            throw new Error(
                data.message ||
                "Could not save monthly report."
            );
        }

        const report =
            data.report || {};

        showMonthlyReportStatus(
            "REPORT GENERATED — Expected Cash: R" +
            Number(report.expected_cash || 0).toFixed(2) +
            " | Actual Cash: R" +
            Number(report.cash_at_hand || 0).toFixed(2) +
            " | Variance: R" +
            Number(report.cash_variance || 0).toFixed(2) +
            " | Damaged Units: " +
            (report.damaged_units || 0)
        );

        cashInput.value = "";
        damagedGoodsSelection = [];
        updateDamagedGoodsSummary();

        await loadProducts();
        await loadMonthlyReports();

    } catch (error) {

        console.error(
            "SAVE MONTHLY REPORT ERROR:",
            error
        );

        showMonthlyReportStatus(
            error.message ||
            "Could not save monthly report."
        );

    } finally {

        button.disabled = false;
        button.textContent =
            "GENERATE MONTHLY REPORT";

    }

}


// ============================================================
// PARSE DAMAGED GOODS
// ============================================================

let damagedGoodsSelection = [];
let damagedGoodsProducts = [];

// ============================================================
// DAMAGED GOODS POPUP
// ============================================================

async function openDamagedGoodsPopup() {

    let popup =
        document.getElementById(
            "damaged-goods-popup"
        );

    if (!popup) {

        popup = document.createElement("div");
        popup.id = "damaged-goods-popup";

        popup.style.cssText = `
            position: fixed;
            inset: 0;
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background: rgba(0,0,0,0.72);
        `;

        popup.innerHTML = `
            <div style="
                width: min(520px, 100%);
                max-height: 90vh;
                overflow-y: auto;
                background: #ffffff;
                border-radius: 14px;
                padding: 20px;
                box-sizing: border-box;
                box-shadow: 0 20px 60px rgba(0,0,0,0.35);
            ">

                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    margin-bottom:16px;
                ">
                    <div>
                        <h2 style="margin:0;">Damaged Goods</h2>
                        <p style="margin:5px 0 0; opacity:.7;">
                            Record damaged stock before generating the monthly report.
                        </p>
                    </div>

                    <button
                        id="close-damaged-goods-popup"
                        type="button"
                        style="
                            border:0;
                            background:transparent;
                            font-size:30px;
                            cursor:pointer;
                        ">×</button>
                </div>

                <div style="display:grid; gap:10px;">
                    <label for="damaged-product-select">Product</label>
                    <select
                        id="damaged-product-select"
                        style="padding:12px; border-radius:8px; border:1px solid #ccc;">
                    </select>

                    <label for="damaged-quantity-input">Quantity Damaged</label>
                    <input
                        id="damaged-quantity-input"
                        type="number"
                        min="1"
                        step="1"
                        value="1"
                        style="padding:12px; border-radius:8px; border:1px solid #ccc;">

                    <button
                        id="add-damaged-item"
                        type="button"
                        style="padding:12px; border:0; border-radius:8px; cursor:pointer;">
                        ADD DAMAGED ITEM
                    </button>
                </div>

                <div style="margin-top:18px;">
                    <h3 style="margin-bottom:10px;">Items Recorded</h3>
                    <div id="damaged-goods-list"></div>
                </div>

                <button
                    id="done-damaged-goods"
                    type="button"
                    style="
                        width:100%;
                        margin-top:18px;
                        padding:14px;
                        border:0;
                        border-radius:8px;
                        cursor:pointer;
                        font-weight:bold;
                    ">
                    DONE
                </button>

            </div>
        `;

        document.body.appendChild(popup);

        document
            .getElementById("close-damaged-goods-popup")
            .addEventListener("click", closeDamagedGoodsPopup);

        document
            .getElementById("done-damaged-goods")
            .addEventListener("click", closeDamagedGoodsPopup);

        document
            .getElementById("add-damaged-item")
            .addEventListener("click", addDamagedGoodsItem);

        popup.addEventListener("click", function(event) {
            if (event.target === popup) {
                closeDamagedGoodsPopup();
            }
        });
    }

    popup.style.display = "flex";

    await loadDamagedGoodsProducts();
    renderDamagedGoodsList();
}

function closeDamagedGoodsPopup() {

    const popup =
        document.getElementById(
            "damaged-goods-popup"
        );

    if (popup) {
        popup.style.display = "none";
    }

    updateDamagedGoodsSummary();
}

async function loadDamagedGoodsProducts() {

    const select =
        document.getElementById(
            "damaged-product-select"
        );

    if (!select) {
        return;
    }

    select.innerHTML =
        "<option>Loading products...</option>";

    try {
        const response =
            await fetch(
                "/api/products?t=" + Date.now()
            );

        const data =
            await response.json();

        if (!response.ok || !data.success) {
            throw new Error(
                data.message ||
                "Could not load products."
            );
        }

        damagedGoodsProducts = data.products || [];

        if (!data.products || data.products.length === 0) {
            select.innerHTML =
                "<option value=\"\">No products available</option>";
            return;
        }

        select.innerHTML =
            data.products.map(function(product) {
                return `
                    <option value="${product.id}">
                        ${escapeHtml(product.name)} — Stock: ${product.stock}
                    </option>
                `;
            }).join("");

    } catch (error) {
        console.error(
            "DAMAGED GOODS PRODUCTS ERROR:",
            error
        );

        select.innerHTML =
            "<option value=\"\">Could not load products</option>";
    }
}

function addDamagedGoodsItem() {

    const select =
        document.getElementById(
            "damaged-product-select"
        );

    const quantityInput =
        document.getElementById(
            "damaged-quantity-input"
        );

    if (!select || !quantityInput || !select.value) {
        return;
    }

    const productId =
        Number(select.value);

    const quantity =
        parseInt(quantityInput.value, 10);

    if (isNaN(quantity) || quantity <= 0) {
        showMessage("Enter a valid damaged quantity.");
        return;
    }

    const existing =
        damagedGoodsSelection.find(function(item) {
            return Number(item.product_id) === productId;
        });

    if (existing) {
        existing.quantity += quantity;
    } else {
        damagedGoodsSelection.push({
            product_id: productId,
            quantity: quantity
        });
    }

    quantityInput.value = "1";
    renderDamagedGoodsList();
}

function removeDamagedGoodsItem(productId) {

    damagedGoodsSelection =
        damagedGoodsSelection.filter(function(item) {
            return Number(item.product_id) !== Number(productId);
        });

    renderDamagedGoodsList();
    updateDamagedGoodsSummary();
}

function renderDamagedGoodsList() {

    const list =
        document.getElementById(
            "damaged-goods-list"
        );

    if (!list) {
        return;
    }

    if (damagedGoodsSelection.length === 0) {
        list.innerHTML =
            '<p style="opacity:.65;">No damaged items recorded.</p>';
        return;
    }

    list.innerHTML =
        damagedGoodsSelection.map(function(item) {
            return `
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    gap:10px;
                    padding:10px;
                    margin-bottom:8px;
                    border:1px solid #ddd;
                    border-radius:8px;
                ">
                    <strong>${escapeHtml(getDamagedProductName(item.product_id))}</strong>
                    <span>Qty: ${item.quantity}</span>
                    <button
                        type="button"
                        onclick="removeDamagedGoodsItem(${item.product_id})"
                        style="border:0; background:transparent; cursor:pointer; font-size:20px;">
                        ×
                    </button>
                </div>
            `;
        }).join("");
}


function getDamagedProductName(productId) {

    const product =
        damagedGoodsProducts.find(function(item) {
            return Number(item.id) === Number(productId);
        });

    return product
        ? product.name
        : "Product #" + productId;
}

function updateDamagedGoodsSummary() {

    const summary =
        document.getElementById(
            "damaged-goods-summary"
        );

    if (!summary) {
        return;
    }

    const units =
        damagedGoodsSelection.reduce(
            function(total, item) {
                return total + Number(item.quantity || 0);
            },
            0
        );

    summary.textContent =
        units > 0
            ? units + " damaged unit(s) recorded."
            : "No damaged goods selected.";
}


// ============================================================
// LOAD SAVED MONTHLY REPORTS
// ============================================================

async function loadMonthlyReports() {

    const content =
        document.getElementById(
            "stock-report-content"
        );

    if (!content) {
        return;
    }

    try {

        const response =
            await fetch(
                "/api/monthly-reports?t=" +
                Date.now()
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {
            throw new Error(
                data.message ||
                "Could not load monthly reports."
            );
        }

        const form =
            content.querySelector(
                ".monthly-report-form"
            );

        const heading =
            content.querySelector(
                ".monthly-history-heading"
            );

        let historyContainer =
            content.querySelector(
                ".monthly-report-list"
            );

        if (!historyContainer) {

            historyContainer =
                document.createElement("div");

            historyContainer.className =
                "monthly-report-list";

            if (heading) {
                heading.after(historyContainer);
            } else if (form) {
                form.after(historyContainer);
            } else {
                content.appendChild(historyContainer);
            }

        }

        if (
            !data.reports ||
            data.reports.length === 0
        ) {

            historyContainer.innerHTML = `

                <div class="report-empty">

                    No monthly reports saved yet.

                </div>

            `;

            return;
        }

        let html = "";

        data.reports.forEach(function(report) {

            const cashVariance =
                Number(report.cash_variance);

            const varianceText =
                (cashVariance >= 0 ? "+" : "") +
                "R" +
                cashVariance.toFixed(2);

            let damagedHtml =
                "<p>No damaged goods recorded.</p>";

            if (
                report.damaged_items &&
                report.damaged_items.length > 0
            ) {

                damagedHtml =
                    report.damaged_items
                        .map(function(item) {

                            return `

                                <div class="damaged-report-item">

                                    <span>
                                        ${escapeHtml(
                                            item.product_name
                                        )}
                                    </span>

                                    <strong>
                                        ${item.quantity}
                                        &nbsp;—&nbsp;
                                        R${Number(
                                            item.value
                                        ).toFixed(2)}
                                    </strong>

                                </div>

                            `;

                        })
                        .join("");

            }

            html += `

                <div class="monthly-report-card">

                    <div class="monthly-report-card-header">

                        <div>

                            <strong>
                                ${escapeHtml(
                                    report.report_month
                                )}
                            </strong>

                            <span>
                                Saved ${escapeHtml(
                                    report.created_at
                                )}
                            </span>

                        </div>

                        <strong class="monthly-loss-value">
                            R${Number(
                                report.total_loss
                            ).toFixed(2)}
                        </strong>

                    </div>

                    <div class="monthly-report-grid">

                        <div class="report-stat">
                            <span>EXPECTED CASH</span>
                            <strong>R${Number(
                                report.expected_cash || 0
                            ).toFixed(2)}</strong>
                        </div>

                        <div class="report-stat">
                            <span>CASH AT HAND</span>
                            <strong>R${Number(
                                report.cash_at_hand || 0
                            ).toFixed(2)}</strong>
                        </div>

                        <div class="report-stat">
                            <span>CASH VARIANCE</span>
                            <strong>${varianceText}</strong>
                        </div>

                        <div class="report-stat">
                            <span>CASH SALES</span>
                            <strong>${report.cash_sales_count || 0} — R${Number(
                                report.cash_sales_amount || 0
                            ).toFixed(2)}</strong>
                        </div>

                        <div class="report-stat">
                            <span>CARD SALES</span>
                            <strong>${report.card_sales_count || 0} — R${Number(
                                report.card_sales_amount || 0
                            ).toFixed(2)}</strong>
                        </div>

                        <div class="report-stat">
                            <span>TOTAL SALES</span>
                            <strong>${report.total_sales_count || 0} — R${Number(
                                report.total_sales_amount || 0
                            ).toFixed(2)}</strong>
                        </div>

                        <div class="report-stat">
                            <span>UNITS SOLD</span>
                            <strong>${report.total_sales_units || 0}</strong>
                        </div>

                        <div class="report-stat">
                            <span>STOCK UNITS</span>
                            <strong>${report.stock_units}</strong>
                        </div>

                        <div class="report-stat">
                            <span>STOCK VALUE</span>
                            <strong>R${Number(
                                report.stock_value
                            ).toFixed(2)}</strong>
                        </div>

                        <div class="report-stat">
                            <span>DAMAGED UNITS</span>
                            <strong>${report.damaged_units}</strong>
                        </div>

                        <div class="report-stat">
                            <span>DAMAGED VALUE</span>
                            <strong>R${Number(
                                report.damaged_value
                            ).toFixed(2)}</strong>
                        </div>

                        <div class="report-stat">
                            <span>TOTAL LOSS</span>
                            <strong>R${Number(
                                report.total_loss
                            ).toFixed(2)}</strong>
                        </div>

                    </div>

                    <div class="damaged-report-list">

                        <strong>
                            Damaged Stock
                        </strong>

                        ${damagedHtml}

                    </div>

                </div>

            `;

        });

        historyContainer.innerHTML = html;

    } catch (error) {

        console.error(
            "MONTHLY REPORTS ERROR:",
            error
        );

        const existing =
            content.querySelector(
                ".monthly-report-list"
            );

        if (existing) {
            existing.innerHTML = `
                <div class="report-error">
                    Could not load monthly reports.
                </div>
            `;
        }

    }

}


function showMonthlyReportStatus(message) {

    const status =
        document.getElementById(
            "monthly-report-status"
        );

    if (status) {
        status.textContent = message;
    }

}


// ============================================================
// 20. ADD STOCK
// ============================================================

async function addStockFromCard(
    product,
    row
) {

    const quantityText =
        prompt(
            "How many units are being added?"
        );


    if (quantityText === null) {
        return;
    }


    const quantity =
        parseInt(
            quantityText,
            10
        );


    if (
        isNaN(quantity) ||
        quantity <= 0
    ) {

        showMessage(
            "Enter a valid quantity."
        );

        return;
    }


    const reason =
        row.querySelector(
            ".stock-reason"
        ).value.trim();


    const finalReason =
        reason ||
        "Stock received";


    try {

        const response =
            await fetch(
                "/api/stock/add",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        product_id:
                            product.id,

                        quantity:
                            quantity,

                        reason:
                            finalReason

                    })

                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            showMessage(

                data.message ||
                "Could not add stock."

            );

            return;
        }


        showMessage(

            product.name +
            "\n\n" +
            "Stock Before: " +
            data.stock.stock_before +
            "\n" +
            "Added: " +
            data.stock.quantity_added +
            "\n" +
            "Stock After: " +
            data.stock.stock_after +
            "\n\n" +
            "Recorded: " +
            data.stock.created_at

        );


        await loadProducts();

        await loadStockTake();

    } catch (error) {

        console.error(
            "ADD STOCK ERROR:",
            error
        );

        showMessage(
            "Could not connect to Easy Sales."
        );

    }

}


// ============================================================
// 21. REMOVE STOCK
// ============================================================

async function removeStockFromCard(
    product,
    row
) {

    const quantityText =
        prompt(
            "How many units are being removed?"
        );


    if (quantityText === null) {
        return;
    }


    const quantity =
        parseInt(
            quantityText,
            10
        );


    if (
        isNaN(quantity) ||
        quantity <= 0
    ) {

        showMessage(
            "Enter a valid quantity."
        );

        return;
    }


    const reason =
        row.querySelector(
            ".stock-reason"
        ).value.trim();


    const finalReason =
        reason ||
        "Stock removed";


    try {

        const response =
            await fetch(
                "/api/stock/remove",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        product_id:
                            product.id,

                        quantity:
                            quantity,

                        reason:
                            finalReason

                    })

                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            showMessage(

                data.message ||
                "Could not remove stock."

            );

            return;
        }


        showMessage(

            product.name +
            "\n\n" +
            "Stock Before: " +
            data.stock.stock_before +
            "\n" +
            "Removed: " +
            data.stock.quantity_removed +
            "\n" +
            "Stock After: " +
            data.stock.stock_after +
            "\n\n" +
            "Recorded: " +
            data.stock.created_at

        );


        await loadProducts();

        await loadStockTake();

    } catch (error) {

        console.error(
            "REMOVE STOCK ERROR:",
            error
        );

        showMessage(
            "Could not connect to Easy Sales."
        );

    }

}


// ============================================================
// 22. SAVE PHYSICAL STOCKTAKE
// ============================================================

async function savePhysicalStocktake(
    product,
    row
) {

    const input =
        row.querySelector(
            ".stock-count-input"
        );


    const notes =
        row.querySelector(
            ".stock-reason"
        ).value.trim();


    const countedStock =
        parseInt(
            input.value,
            10
        );


    if (
        isNaN(countedStock) ||
        countedStock < 0
    ) {

        showMessage(
            "Enter a valid physical stock count."
        );

        return;
    }


    const confirmed =
        confirm(

            "Record physical stocktake?\n\n" +
            product.name +
            "\n" +
            "System Stock: " +
            product.stock +
            "\n" +
            "Physical Count: " +
            countedStock

        );


    if (!confirmed) {
        return;
    }


    const button =
        row.querySelector(
            ".stock-save-button"
        );


    button.disabled = true;

    button.textContent =
        "RECORDING...";


    try {

        const response =
            await fetch(
                "/api/stocktake/record",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        product_id:
                            product.id,

                        counted_stock:
                            countedStock,

                        notes:
                            notes

                    })

                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            showMessage(

                data.message ||
                "Could not record stocktake."

            );

            return;
        }


        const result =
            data.stocktake;


        showMessage(

            "STOCKTAKE RECORDED\n\n" +

            product.name +
            "\n\n" +

            "System Stock: " +
            result.system_stock +
            "\n" +

            "Physical Count: " +
            result.counted_stock +
            "\n" +

            "Variance: " +
            result.variance +
            "\n" +

            "Final Stock: " +
            result.stock_after +
            "\n\n" +

            "Date & Time:\n" +
            result.taken_at

        );


        await loadProducts();

        await loadStockTake();

    } catch (error) {

        console.error(
            "PHYSICAL STOCKTAKE ERROR:",
            error
        );

        showMessage(
            "Could not connect to Easy Sales."
        );

    } finally {

        button.disabled = false;

        button.textContent =
            "SAVE PHYSICAL STOCKTAKE";

    }

}


// ============================================================
// 23. MOVEMENT HISTORY
// ============================================================

async function toggleMovementHistory(
    productId,
    row
) {

    const panel =
        row.querySelector(
            ".movement-history-panel"
        );


    if (
        panel.classList.contains("show")
    ) {

        panel.classList.remove(
            "show"
        );

        return;
    }


    panel.classList.add(
        "show"
    );


    panel.innerHTML =
        "Loading movement history...";


    try {

        const response =
            await fetch(
                "/api/stock-movements?product_id=" +
                encodeURIComponent(productId)
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            panel.innerHTML =
                escapeHtml(
                    data.message ||
                    "Could not load history."
                );

            return;
        }


        if (
            !data.movements ||
            data.movements.length === 0
        ) {

            panel.innerHTML =
                "No stock movements recorded yet.";

            return;
        }


        panel.innerHTML = "";


        data.movements.forEach(
            function(movement) {

                const entry =
                    document.createElement(
                        "div"
                    );

                entry.className =
                    "stock-history-entry";


                entry.innerHTML = `

                    <strong>
                        ${escapeHtml(
                            movement.movement_type
                        )}
                    </strong>

                    <span>
                        Date & Time:
                        ${escapeHtml(
                            movement.created_at
                        )}
                    </span>

                    <span>
                        Stock Before:
                        ${movement.stock_before}
                    </span>

                    <span>
                        Added:
                        ${movement.quantity_added}
                    </span>

                    <span>
                        Sold:
                        ${movement.quantity_sold}
                    </span>

                    <span>
                        Adjustment:
                        ${movement.adjustment}
                    </span>

                    <span>
                        Stock After:
                        ${movement.stock_after}
                    </span>

                    <span>
                        Reason:
                        ${escapeHtml(
                            movement.reason ||
                            ""
                        )}
                    </span>

                `;


                panel.appendChild(entry);

            }
        );


    } catch (error) {

        console.error(
            "MOVEMENT HISTORY ERROR:",
            error
        );

        panel.innerHTML =
            "Could not connect to Easy Sales.";

    }

}


// ============================================================
// 24. STOCKTAKE HISTORY
// ============================================================

async function toggleStocktakeHistory(
    productId,
    row
) {

    const panel =
        row.querySelector(
            ".stocktake-history-panel"
        );


    if (
        panel.classList.contains("show")
    ) {

        panel.classList.remove(
            "show"
        );

        return;
    }


    panel.classList.add(
        "show"
    );


    panel.innerHTML =
        "Loading stocktake history...";


    try {

        const response =
            await fetch(
                "/api/stocktake-history?product_id=" +
                encodeURIComponent(productId)
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            panel.innerHTML =
                escapeHtml(
                    data.message ||
                    "Could not load stocktake history."
                );

            return;
        }


        if (
            !data.history ||
            data.history.length === 0
        ) {

            panel.innerHTML =
                "No physical stocktakes recorded yet.";

            return;
        }


        panel.innerHTML = "";


        data.history.forEach(
            function(record) {

                const entry =
                    document.createElement(
                        "div"
                    );


                entry.className =
                    "stock-history-entry";


                entry.innerHTML = `

                    <strong>
                        PHYSICAL STOCKTAKE
                    </strong>

                    <span>
                        Date & Time:
                        ${escapeHtml(
                            record.taken_at
                        )}
                    </span>

                    <span>
                        System Stock:
                        ${record.system_stock}
                    </span>

                    <span>
                        Physical Count:
                        ${record.counted_stock}
                    </span>

                    <span>
                        Variance:
                        ${record.variance}
                    </span>

                    <span>
                        Final Stock:
                        ${record.counted_stock}
                    </span>

                    <span>
                        Notes:
                        ${escapeHtml(
                            record.notes ||
                            ""
                        )}
                    </span>

                `;


                panel.appendChild(entry);

            }
        );


    } catch (error) {

        console.error(
            "STOCKTAKE HISTORY ERROR:",
            error
        );

        panel.innerHTML =
            "Could not connect to Easy Sales.";

    }

}


// ============================================================
// OPTIONAL SALE FEE
// ============================================================

function getSaleFee() {

    const input = document.getElementById("sale-fee");

    if (!input) {
        return 0;
    }

    const fee = parseFloat(input.value);

    return isNaN(fee) || fee < 0 ? 0 : fee;

}


function getCheckoutTotal() {
    return getCartTotal() + getSaleFee();
}


function updateCheckoutTotals() {

    const subtotal = getCartTotal();
    const total = getCheckoutTotal();

    const subtotalElement = document.getElementById("checkout-subtotal");
    const totalElement = document.getElementById("checkout-total");

    if (subtotalElement) {
        subtotalElement.textContent = "R" + subtotal.toFixed(2);
    }

    if (totalElement) {
        totalElement.textContent = "R" + total.toFixed(2);
    }

    calculateChange();
}


// ============================================================
// 25. CHECKOUT
// ============================================================

function openCheckout() {

    if (cart.length === 0) {

        showMessage(
            "Your cart is empty."
        );

        return;
    }


    updateCheckoutTotals();


    const checkout =
        document.getElementById(
            "checkout-window"
        );


    if (checkout) {

        checkout.classList.add(
            "show"
        );

    }


    selectCashPayment();

}


function closeCheckout() {

    const checkout =
        document.getElementById(
            "checkout-window"
        );

    if (checkout) {

        checkout.classList.remove(
            "show"
        );

    }

}


// ============================================================
// 26. PAYMENT
// ============================================================

function selectCashPayment() {

    selectedPaymentMethod =
        "cash";


    const cashButton =
        document.getElementById(
            "cash-payment"
        );

    const cardButton =
        document.getElementById(
            "card-payment"
        );

    const cashSection =
        document.getElementById(
            "cash-section"
        );

    const cardSection =
        document.getElementById(
            "card-section"
        );


    if (cashButton) {

        cashButton.classList.add(
            "selected"
        );

    }


    if (cardButton) {

        cardButton.classList.remove(
            "selected"
        );

    }


    if (cashSection) {

        cashSection.style.display =
            "block";

    }


    if (cardSection) {

        cardSection.classList.remove(
            "show"
        );

    }


    const cashInput =
        document.getElementById(
            "cash-received"
        );


    if (cashInput) {

        cashInput.value =
            "";

    }


    const change =
        document.getElementById(
            "change-amount"
        );


    if (change) {

        change.textContent =
            "R0.00";

    }

}


function selectCardPayment() {

    selectedPaymentMethod =
        "card";


    const cardButton =
        document.getElementById(
            "card-payment"
        );

    const cashButton =
        document.getElementById(
            "cash-payment"
        );

    const cashSection =
        document.getElementById(
            "cash-section"
        );

    const cardSection =
        document.getElementById(
            "card-section"
        );


    if (cardButton) {

        cardButton.classList.add(
            "selected"
        );

    }


    if (cashButton) {

        cashButton.classList.remove(
            "selected"
        );

    }


    if (cashSection) {

        cashSection.style.display =
            "none";

    }


    if (cardSection) {

        cardSection.classList.add(
            "show"
        );

    }

}


// ============================================================
// 27. CHANGE
// ============================================================

function calculateChange() {

    const input =
        document.getElementById(
            "cash-received"
        );

    const output =
        document.getElementById(
            "change-amount"
        );


    if (!input || !output) {
        return;
    }


    const received =
        parseFloat(input.value) || 0;


    const total =
        getCheckoutTotal();


    const change =
        received - total;


    if (change >= 0) {

        output.textContent =
            "R" +
            change.toFixed(2);

    } else {

        output.textContent =
            "R0.00";

    }

}


// ============================================================
// 28. COMPLETE SALE
// ============================================================

async function completeSale() {

    if (cart.length === 0) {

        showMessage(
            "Your cart is empty."
        );

        return;
    }


    if (
        selectedPaymentMethod ===
        "cash"
    ) {

        const cashInput =
            document.getElementById(
                "cash-received"
            );


        const received =
            parseFloat(
                cashInput.value
            ) || 0;


        const total =
            getCheckoutTotal();


        if (received < total) {

            showMessage(
                "Cash received is not enough."
            );

            return;
        }

    }


    const button =
        document.getElementById(
            "complete-sale"
        );


    if (button) {

        button.disabled = true;

        button.textContent =
            "PROCESSING...";

    }


    try {

        const response =
            await fetch(
                "/api/sales",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        cart: cart,

                        payment_method:
                            selectedPaymentMethod,

                        sale_fee:
                            getSaleFee()

                    })

                }
            );


        const data =
            await response.json();


        if (
            !response.ok ||
            !data.success
        ) {

            showMessage(

                data.message ||
                "Sale could not be completed."

            );

            return;
        }


        cart = [];

        updateCart();

        closeCheckout();

        closeCart();


        selectedPaymentMethod =
            "cash";


        const cashInput =
            document.getElementById(
                "cash-received"
            );


        if (cashInput) {

            cashInput.value = "";

        }


        const change =
            document.getElementById(
                "change-amount"
            );


        if (change) {

            change.textContent =
                "R0.00";

        }


        const saleFeeInput = document.getElementById("sale-fee");

        if (saleFeeInput) {
            saleFeeInput.value = "0";
        }

        selectCashPayment();
        updateCheckoutTotals();


        await loadProducts();


        const stockWindow =
            document.getElementById(
                "stock-take-window"
            );


        if (
            stockWindow &&
            stockWindow.classList.contains(
                "show"
            )
        ) {

            await loadStockTake();

        }


        if (button) {

            button.textContent =
                "SALE COMPLETED";

        }


        setTimeout(
            function() {

                if (button) {

                    button.textContent =
                        "Complete Sale";

                }

            },
            1200
        );


    } catch (error) {

        console.error(
            "COMPLETE SALE ERROR:",
            error
        );

        showMessage(
            "Could not connect to Easy Sales."
        );

    } finally {

        if (button) {

            button.disabled = false;

        }

    }

}


// ============================================================
// 29. PRODUCT SEARCH
// ============================================================

function setupProductSearch() {

    const searchInput =
        document.getElementById(
            "product-search"
        );


    if (!searchInput) {
        return;
    }


    searchInput.addEventListener(
        "input",
        function() {

            const search =
                this.value
                    .toLowerCase()
                    .trim();


            const rows =
                document.querySelectorAll(
                    ".product-row"
                );


            rows.forEach(
                function(row) {

                    const name =
                        row.querySelector(
                            ".product-information strong"
                        );


                    if (!name) {
                        return;
                    }


                    const productName =
                        name.textContent
                            .toLowerCase();


                    if (
                        productName.includes(
                            search
                        )
                    ) {

                        row.style.display =
                            "";

                    } else {

                        row.style.display =
                            "none";

                    }

                }
            );

        }
    );

}


// ============================================================
// 30. ESCAPE HTML
// ============================================================

function escapeHtml(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value == null
            ? ""
            : String(value);

    return div.innerHTML;

}


// ============================================================
// 31. ADD PRODUCT MESSAGE
// ============================================================

function showAddProductMessage(
    message
) {

    const status =
        document.getElementById(
            "add-product-status"
        );


    if (status) {

        status.textContent =
            message;

    }


    console.log(
        "Easy Sales:",
        message
    );

}


// ============================================================
// 32. EDIT PRODUCT
// ============================================================

let editingProductId = null;


function openEditProduct(product) {

    editingProductId = product.id;

    const popup =
        document.getElementById(
            "edit-product-window"
        );

    const nameInput =
        document.getElementById(
            "edit-product-name"
        );

    const priceInput =
        document.getElementById(
            "edit-product-price"
        );

    const stockInput =
        document.getElementById(
            "edit-product-stock"
        );

    if (
        !popup ||
        !nameInput ||
        !priceInput ||
        !stockInput
    ) {

        console.error(
            "Edit Product window not found."
        );

        return;

    }

    nameInput.value = product.name;
    priceInput.value = Number(product.price).toFixed(2);
    stockInput.value = product.stock;

    showEditProductMessage("");

    popup.classList.add(
        "show"
    );

}


function closeEditProduct() {

    const popup =
        document.getElementById(
            "edit-product-window"
        );

    if (popup) {

        popup.classList.remove(
            "show"
        );

    }

    editingProductId = null;

}


async function saveEditedProduct() {

    if (editingProductId === null) {

        showEditProductMessage(
            "No product selected."
        );

        return;

    }

    const nameInput =
        document.getElementById(
            "edit-product-name"
        );

    const priceInput =
        document.getElementById(
            "edit-product-price"
        );

    const stockInput =
        document.getElementById(
            "edit-product-stock"
        );

    const saveButton =
        document.getElementById(
            "save-edit-product"
        );

    if (
        !nameInput ||
        !priceInput ||
        !stockInput ||
        !saveButton
    ) {
        return;
    }

    const name =
        nameInput.value.trim();

    const price =
        parseFloat(priceInput.value);

    const stock =
        parseInt(stockInput.value, 10);

    if (!name) {

        showEditProductMessage(
            "Enter a product name."
        );

        return;

    }

    if (
        isNaN(price) ||
        price < 0
    ) {

        showEditProductMessage(
            "Enter a valid price."
        );

        return;

    }

    if (
        isNaN(stock) ||
        stock < 0
    ) {

        showEditProductMessage(
            "Enter a valid stock quantity."
        );

        return;

    }

    saveButton.disabled = true;
    saveButton.textContent =
        "SAVING...";

    try {

        const response =
            await fetch(
                "/api/products/" +
                encodeURIComponent(editingProductId),
                {
                    method: "PUT",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        name: name,
                        price: price,
                        stock: stock
                    })
                }
            );

        const data =
            await response.json();

        if (
            !response.ok ||
            !data.success
        ) {

            showEditProductMessage(
                data.message ||
                "Could not update product."
            );

            return;

        }

        showEditProductMessage(
            "Product updated successfully."
        );

        await loadProducts();

        const stockWindow =
            document.getElementById(
                "stock-take-window"
            );

        if (
            stockWindow &&
            stockWindow.classList.contains(
                "show"
            )
        ) {

            await showCurrentStockReport();

        }

        setTimeout(
            function() {

                closeEditProduct();

            },
            400
        );

    } catch (error) {

        console.error(
            "EDIT PRODUCT ERROR:",
            error
        );

        showEditProductMessage(
            "Could not connect to Easy Sales."
        );

    } finally {

        saveButton.disabled = false;
        saveButton.textContent =
            "SAVE CHANGES";

    }

}


function showEditProductMessage(message) {

    const status =
        document.getElementById(
            "edit-product-status"
        );

    if (status) {

        status.textContent =
            message;

    }

}


// ============================================================
// 32. GENERAL MESSAGE
// ============================================================

function showMessage(message) {

    console.log(
        "Easy Sales:",
        message
    );


    alert(
        message
    );

}

// ============================================================
// 33. LIVE STORE ACCESS CHECK
// ============================================================
//
// The server is the authority for store access. This small heartbeat means
// that a store which is deactivated from the Controller is automatically
// returned to the Store Access page without waiting for the cashier to make
// another sale or refresh the page.
//

let storeAccessCheckRunning = false;

async function checkLiveStoreAccess() {

    if (storeAccessCheckRunning) {
        return;
    }

    storeAccessCheckRunning = true;

    try {

        const response = await fetch(
            "/api/session-status?t=" + Date.now(),
            {
                method: "GET",
                cache: "no-store",
                headers: {
                    "Cache-Control": "no-cache"
                }
            }
        );

        if (
            response.status === 401 ||
            response.status === 403
        ) {

            window.location.replace(
                "/store-access?status=inactive"
            );

        }

    } catch (error) {

        // A network problem must not log the cashier out. The next
        // successful request will be checked again by the server.

        console.warn(
            "STORE ACCESS CHECK:",
            error
        );

    } finally {

        storeAccessCheckRunning = false;

    }

}


// Check regularly while the POS is open.
setInterval(
    checkLiveStoreAccess,
    20000
);


// Also check immediately when the user returns to the POS tab.
document.addEventListener(
    "visibilitychange",
    function() {

        if (!document.hidden) {
            checkLiveStoreAccess();
        }

    }
);


// Perform the first check shortly after the POS loads.
setTimeout(
    checkLiveStoreAccess,
    1500
);
/* ============================================================
   POS BARCODE SCANNER
   ============================================================ */

const scannerButton =
    document.getElementById("scanner-button");

const scannerWindow =
    document.getElementById("scanner-window");

const closeScannerButton =
    document.getElementById("close-scanner");

const scannerVideo =
    document.getElementById("scanner-video");

const scannerStatus =
    document.getElementById("scanner-status");


let scannerStream = null;
let barcodeDetector = null;
let scannerRunning = false;
let barcodeDetected = false;


/* ============================================================
   OPEN SCANNER
   ============================================================ */

async function openScanner() {

    if (
        !scannerWindow ||
        !scannerVideo ||
        !scannerStatus
    ) {
        console.error(
            "Scanner elements were not found."
        );
        return;
    }


    // Reset scanner every time it opens
    barcodeDetected = false;
    scannerRunning = false;

    scannerWindow.classList.add("show");

    scannerStatus.textContent =
        "Opening camera...";


    try {

        // Open the rear camera
        scannerStream =
            await navigator.mediaDevices.getUserMedia({

                video: {
                    facingMode: {
                        ideal: "environment"
                    },
                    width: {
                        ideal: 1920
                    },
                    height: {
                        ideal: 1080
                    }
                },

                audio: false

            });


        scannerVideo.srcObject =
            scannerStream;


        // Wait until the video actually has camera data
        await new Promise(
            function(resolve) {

                scannerVideo.onloadedmetadata =
                    function() {
                        resolve();
                    };

            }
        );


        await scannerVideo.play();


        scannerStatus.textContent =
            "Camera ready — point at a barcode";


        // Check whether BarcodeDetector exists
        if (!("BarcodeDetector" in window)) {

            scannerStatus.textContent =
                "Barcode detection is not supported by this browser.";

            console.error(
                "BarcodeDetector is not supported."
            );

            return;
        }


        // Ask the browser which formats it supports
        const supportedFormats =
            await BarcodeDetector.getSupportedFormats();


        const wantedFormats = [
            "ean_13",
            "ean_8",
            "code_128",
            "code_39",
            "upc_a",
            "upc_e"
        ];


        // Only use formats actually supported by the phone/browser
        const formats =
            wantedFormats.filter(
                format =>
                    supportedFormats.includes(format)
            );


        barcodeDetector =
            new BarcodeDetector({
                formats: formats
            });


        scannerRunning = true;


        scannerStatus.textContent =
            "Scanning... hold the barcode inside the camera.";

        scanBarcode();


    } catch (error) {

        console.error(
            "Scanner error:",
            error
        );

        scannerStatus.textContent =
            "Scanner error: " +
            error.message;

    }

}


/* ============================================================
   SCAN BARCODE
   ============================================================ */

async function scanBarcode() {

    // Stop if scanner was closed
    if (
        !scannerRunning ||
        barcodeDetected
    ) {
        return;
    }


    // Wait until the video has a real camera frame
    if (
        scannerVideo.readyState <
        HTMLMediaElement.HAVE_ENOUGH_DATA
    ) {

        requestAnimationFrame(
            scanBarcode
        );

        return;
    }


    try {

        const barcodes =
            await barcodeDetector.detect(
                scannerVideo
            );


        if (barcodes.length > 0) {

            const barcode =
                barcodes[0].rawValue;


            // Prevent the same barcode from firing repeatedly
            barcodeDetected = true;
            scannerRunning = false;


            scannerStatus.textContent =
                "✓ Barcode detected: " +
                barcode;


            console.log(
                "EASY SALES BARCODE:",
                barcode
            );


            // STOP CAMERA AFTER A SUCCESSFUL SCAN
            if (scannerStream) {

                scannerStream
                    .getTracks()
                    .forEach(
                        track => track.stop()
                    );

                scannerStream = null;

            }


            /*
            ------------------------------------------------
            TEMPORARY TEST

            We are testing barcode detection first.

            Once this successfully detects your barcode,
            we will connect this value to the owner's
            product barcode and then the product/cart.
            ------------------------------------------------
            */

            return;

        }


    } catch (error) {

        console.error(
            "Barcode detection error:",
            error
        );

    }


    // Keep scanning
    if (
        scannerRunning &&
        !barcodeDetected
    ) {

        requestAnimationFrame(
            scanBarcode
        );

    }

}


/* ============================================================
   CLOSE SCANNER
   ============================================================ */

function closeScanner() {

    scannerRunning = false;
    barcodeDetected = false;


    if (scannerStream) {

        scannerStream
            .getTracks()
            .forEach(
                track => track.stop()
            );

        scannerStream = null;

    }


    if (scannerVideo) {

        scannerVideo.pause();

        scannerVideo.srcObject =
            null;

    }


    if (scannerWindow) {

        scannerWindow.classList.remove(
            "show"
        );

    }

}


/* ============================================================
   SCANNER BUTTON EVENTS
   ============================================================ */

if (scannerButton) {

    scannerButton.addEventListener(
        "click",
        openScanner
    );

}


if (closeScannerButton) {

    closeScannerButton.addEventListener(
        "click",
        closeScanner
    );

}
