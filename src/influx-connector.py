"""
InfluxDB connection test utility
This file can be used to test InfluxDB connectivity and data writing
"""

import os
from datetime import datetime
from influxdb_client_3 import InfluxDBClient3, Point, InfluxDBError, WriteOptions, write_client_options
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_influxdb_connection():
    """Test InfluxDB connection and write sample data"""

    # Get configuration from environment
    host = os.getenv('INFLUXDB_HOST')
    token = os.getenv('INFLUXDB_TOKEN')
    database = os.getenv('INFLUXDB_DATABASE')

    if not all([host, token, database]):
        print("Error: Missing InfluxDB configuration in .env file")
        print("Required: INFLUXDB_HOST, INFLUXDB_TOKEN, INFLUXDB_DATABASE")
        return False

    print(f"Testing connection to InfluxDB:")
    print(f"  Host: {host}")
    print(f"  Database: {database}")

    # Create test points
    test_points = [
        Point("crypto_price_test")
        .tag("symbol", "BTCUSDT")
        .tag("source", "test")
        .field("price", 45000.50)
        .field("open", 44800.00)
        .field("high", 45200.00)
        .field("low", 44700.00)
        .field("close", 45000.50)
        .field("volume", 1234.56)
        .time(datetime.now()),

        Point("crypto_price_test")
        .tag("symbol", "ETHUSDT")
        .tag("source", "test")
        .field("price", 3200.75)
        .field("open", 3180.00)
        .field("high", 3220.00)
        .field("low", 3175.00)
        .field("close", 3200.75)
        .field("volume", 987.65)
        .time(datetime.now())
    ]

    # Configure callbacks
    def success_callback(self, data: str):
        print(f"✅ Successfully wrote test data to InfluxDB ({len(data)} bytes)")

    def error_callback(self, data: str, exception: InfluxDBError):
        print(f"❌ Failed to write test data: {exception}")

    def retry_callback(self, data: str, exception: InfluxDBError):
        print(f"🔄 Retrying write to InfluxDB: {exception}")

    # Configure write options
    write_options = WriteOptions(
        batch_size=10,
        flush_interval=1_000,
        jitter_interval=0,
        retry_interval=5_000,
        max_retries=3,
        max_retry_delay=30_000,
        exponential_base=2
    )

    wco = write_client_options(
        success_callback=success_callback,
        error_callback=error_callback,
        retry_callback=retry_callback,
        write_options=write_options
    )

    try:
        # Test connection and write data
        with InfluxDBClient3(
                host=host,
                token=token,
                database=database,
                write_client_options=wco
        ) as client:

            print("🔗 Connected to InfluxDB successfully")

            # Write test points
            print("📝 Writing test data...")
            client.write(test_points, write_precision='s')

            print("✅ Test completed successfully!")
            return True

    except Exception as e:
        print(f"❌ Error connecting to InfluxDB: {e}")
        return False


def query_test_data():
    """Query and display test data from InfluxDB"""

    # Get configuration from environment
    host = os.getenv('INFLUXDB_HOST')
    token = os.getenv('INFLUXDB_TOKEN')
    database = os.getenv('INFLUXDB_DATABASE')

    try:
        with InfluxDBClient3(host=host, token=token, database=database) as client:

            # Query recent test data
            query = f"""
            SELECT *
            FROM crypto_price_test
            WHERE time >= now() - interval '1 hour'
            ORDER BY time DESC
            LIMIT 10
            """

            print("🔍 Querying recent test data...")
            result = client.query(query=query, language='sql')

            if result:
                print("📊 Recent test data:")
                for row in result:
                    print(f"  {row}")
            else:
                print("📭 No test data found")

    except Exception as e:
        print(f"❌ Error querying data: {e}")


if __name__ == "__main__":
    print("InfluxDB Connection Test Utility")
    print("=" * 40)

    # Test connection and write
    if test_influxdb_connection():
        print("\n" + "=" * 40)

        # Query test data
        query_test_data()

    print("\n" + "=" * 40)
    print("Test completed. Check your InfluxDB dashboard for the test data.")
