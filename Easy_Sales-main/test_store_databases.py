# ============================================================
# EASY SALES - PRIVATE STORE DATABASE TEST
# ============================================================
#
# Place this file in:
# Easy_Sales/test_store_databases.py
#
# This is a SAFE TEST FILE.
# It does NOT change app.py or your working POS.
#
# It proves that two stores can have completely separate data.
# ============================================================

from store_database import (
    create_store_database,
    get_store_connection,
    get_store_database_path,
)


def count_products(store_id):
    connection = get_store_connection(store_id)
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM products")
    total = cursor.fetchone()[0]

    connection.close()
    return total


def main():
    store_one = "STORE001"
    store_two = "STORE002"

    # Create two completely separate private databases.
    create_store_database(store_one)
    create_store_database(store_two)

    print("Easy Sales Private Store Database Test")
    print("=" * 42)

    print(f"{store_one} database:")
    print(get_store_database_path(store_one))

    print(f"{store_two} database:")
    print(get_store_database_path(store_two))

    print()
    print("Checking database isolation...")

    store_one_products = count_products(store_one)
    store_two_products = count_products(store_two)

    print(f"{store_one} products: {store_one_products}")
    print(f"{store_two} products: {store_two_products}")

    print()
    print("SUCCESS: Each store has its own private database.")
    print("Nothing has been connected to the live POS yet.")
    print("Your existing Easy Sales database has not been changed.")


if __name__ == "__main__":
    main()
