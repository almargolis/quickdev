# CRUD API Example

This example demonstrates QuickDev idioms for building RESTful APIs with consistent patterns.

## The CRUD Problem

Every API needs the same operations:
- **C**reate - POST /api/resource
- **R**ead - GET /api/resource/:id
- **U**pdate - PUT /api/resource/:id
- **D**elete - DELETE /api/resource/:id

Plus:
- List with filtering
- Search
- Validation
- Error handling
- Bulk operations

You end up writing this code for every model. QuickDev makes it an idiom.

## XSynth for Data Models

See `product_model.xpy` - define your model once:

```python
#$define MODEL_NAME Product
#$define FIELDS name, description, price, quantity, category
#$define REQUIRED_FIELDS name, price
#$define SEARCHABLE_FIELDS name, description, category
```

XSynth generates:
- `to_dict()` method
- `from_dict()` with validation
- `search()` across specified fields
- SQL CREATE TABLE statements
- All with field names from ONE source

## Running the Example

```bash
# Install dependencies
pip install flask flask-sqlalchemy

# Run the API
python api.py

# Seed with sample data
flask seed

# Try the endpoints
curl http://localhost:5003/api/products
curl http://localhost:5003/api/stats
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/products | List all products |
| GET | /api/products?category=electronics | Filter by category |
| GET | /api/products?search=laptop | Search products |
| POST | /api/products | Create a product |
| GET | /api/products/:id | Get product by ID |
| PUT | /api/products/:id | Update product |
| DELETE | /api/products/:id | Delete product |
| POST | /api/products/bulk | Bulk create |
| GET | /api/stats | Statistics |

## Example Requests

### Create a Product

```bash
curl -X POST http://localhost:5003/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": 999.99,
    "quantity": 10,
    "category": "electronics"
  }'
```

### List Products

```bash
curl http://localhost:5003/api/products
```

### Search Products

```bash
curl http://localhost:5003/api/products?search=laptop
```

### Get Statistics

```bash
curl http://localhost:5003/api/stats
```

### Update a Product

```bash
curl -X PUT http://localhost:5003/api/products/1 \
  -H "Content-Type: application/json" \
  -d '{"price": 899.99}'
```

### Delete a Product

```bash
curl -X DELETE http://localhost:5003/api/products/1
```

## The QuickDev Pattern

This example shows the idiom approach:

### 1. Model Definition (XSynth)

Define fields once in `.xpy` file:
```python
#$define FIELDS name, description, price, quantity, category
```

### 2. Auto-Generated Methods

XSynth generates:
- `to_dict()` - Serialization
- `from_dict()` - Deserialization with validation
- `search()` - Search across fields

### 3. Standard CRUD Routes

Routes follow a consistent pattern that could be generated:

```python
@app.route('/api/<resource>', methods=['GET'])
def list_resource():
    # Standard list with filtering
    pass

@app.route('/api/<resource>', methods=['POST'])
def create_resource():
    # Standard creation with validation
    pass
```

## Idiom Potential

This example could be packaged as a QuickDev idiom:

```python
from qdapi import create_crud_api

# One line creates all CRUD routes
create_crud_api(app, Product, '/api/products')

# Results in:
# GET    /api/products
# POST   /api/products
# GET    /api/products/:id
# PUT    /api/products/:id
# DELETE /api/products/:id
# + filtering, search, validation, error handling
```

## Expanding the Pattern

Add more models:

```python
# products.xpy
#$define MODEL_NAME Product
#$define FIELDS name, price, quantity

# customers.xpy
#$define MODEL_NAME Customer
#$define FIELDS name, email, phone

# orders.xpy
#$define MODEL_NAME Order
#$define FIELDS customer_id, total, status
```

Process with XSynth → get three complete models with CRUD methods.

## Key Benefits

**Without QuickDev:**
- Write `to_dict()` for every model
- Write `from_dict()` for every model
- Write validation for every model
- Write search for every model
- ~100 lines per model

**With QuickDev:**
- Define fields once
- Run XSynth
- Get all methods auto-generated
- ~20 lines per model

**Savings: 80%+**

## Real-World Usage

This pattern scales to:
- E-commerce (products, orders, customers)
- CMS (posts, pages, media)
- SaaS (users, subscriptions, invoices)
- Internal tools (tickets, assets, tasks)

Any app with multiple models benefits from this idiom.

## Next Steps

1. Add more models to see the pattern scale
2. Create a `qdapi` package with `create_crud_api()`
3. Add pagination, sorting, advanced filtering
4. Add API documentation generation
5. Package as a reusable idiom

QuickDev is about identifying these patterns and making them reusable.
