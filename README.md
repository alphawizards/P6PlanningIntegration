# P6 Local AI Agent

A Python-based local interface for connecting to Primavera P6 software using JPype1.

## Overview

This repository provides a Python interface to connect to local Primavera P6 installations via JPype1, enabling seamless integration between Python applications and P6's Java-based API.

## Features

- ✅ Dynamic JAR file discovery and classpath building
- ✅ Environment-based configuration
- ✅ Robust error handling and logging
- ✅ Automatic JVM lifecycle management
- ✅ P6 Session authentication

## Requirements

- Python 3.7 or higher
- Java Runtime Environment (JRE) or Java Development Kit (JDK)
- Primavera P6 Integration API JAR files
- Access to a Primavera P6 database

## Installation

1. Clone this repository:
```bash
git clone https://github.com/alphawizards/P6PlanningIntegration.git
cd P6PlanningIntegration
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your P6 configuration
```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
# Primavera P6 Library Directory
# Path to directory containing P6 integration JAR files
P6_LIB_DIR=/path/to/p6/lib

# Database Credentials
DB_USER=your_database_username
DB_PASS=your_database_password

# P6 User Credentials
P6_USER=your_p6_username
P6_PASS=your_p6_password
```

### Required Environment Variables

- **P6_LIB_DIR**: Path to the directory containing Primavera P6 Integration API JAR files
- **DB_USER**: Database username for P6 database connection
- **DB_PASS**: Database password for P6 database connection
- **P6_USER**: P6 application username
- **P6_PASS**: P6 application password

## Usage

Run the main script to test the P6 connection:

```bash
python main.py
```

The script will:
1. Load environment variables from `.env`
2. Discover all JAR files in the `P6_LIB_DIR` directory
3. Start the JVM with the dynamically built classpath
4. Import the P6 Session class
5. Attempt to login to P6
6. Display connection status
7. Shutdown the JVM

### Example Output

```
============================================================
P6 Local AI Agent - Primavera P6 Integration
============================================================

Found 15 JAR files in /opt/p6/lib
Starting JVM...
JVM started successfully
Importing Primavera P6 Session class...
Attempting to login to P6 as user: admin
✓ Successfully connected to Primavera P6!
✓ Session established for user: admin
✓ Session logged out successfully
Shutting down JVM...
JVM shutdown complete

============================================================
Status: Connection test completed successfully
```

## Project Structure

```
P6PlanningIntegration/
├── .env.example          # Example environment configuration
├── .gitignore           # Git ignore rules
├── main.py              # Main application entry point
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Dependencies

- **JPype1** (>=1.4.1): Python-Java bridge for JVM interaction
- **pandas** (>=2.0.0): Data manipulation and analysis
- **python-dotenv** (>=1.0.0): Environment variable management

## How It Works

The `connect_to_p6()` function performs the following steps:

1. **Environment Loading**: Loads configuration from `.env` file
2. **Validation**: Verifies all required environment variables are set
3. **JAR Discovery**: Scans `P6_LIB_DIR` for all `.jar` files
4. **Classpath Building**: Dynamically constructs Java classpath from discovered JARs
5. **JVM Initialization**: Starts the Java Virtual Machine with the classpath
6. **P6 Import**: Imports the `com.primavera.integration.client.Session` class
7. **Authentication**: Attempts to login using provided credentials
8. **Cleanup**: Logs out and shuts down the JVM

## Error Handling

The application includes comprehensive error handling:

- Missing environment variables
- Invalid P6 library directory
- No JAR files found
- Java exceptions during connection
- General Python exceptions

All errors are logged with descriptive messages to help troubleshooting.

## Troubleshooting

### "No JAR files found" Error
- Verify `P6_LIB_DIR` points to the correct directory
- Ensure the directory contains P6 Integration API JAR files

### JVM Startup Failures
- Verify Java is installed: `java -version`
- Check that JAR files are not corrupted
- Ensure sufficient memory is available

### Connection Failures
- Verify database credentials are correct
- Check P6 user credentials
- Ensure P6 database is accessible
- Verify network connectivity to the database server

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
