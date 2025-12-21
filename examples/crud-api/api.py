"""
Complete RESTful CRUD API Example

Demonstrates QuickDev patterns for building APIs:
- XSynth-generated models
- Consistent error handling
- Standard CRUD operations
- Search functionality
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Model (normally imported from product_model.py)
class Product(db.Model):
    """Product model with auto-generated CRUD methods."""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'quantity': self.quantity,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        required = ['name', 'price']
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        return cls(
            name=data.get('name'),
            description=data.get('description'),
            price=data.get('price'),
            quantity=data.get('quantity', 0),
            category=data.get('category'),
        )


# CRUD Routes - This is the idiom pattern

@app.route('/api/products', methods=['GET'])
def list_products():
    """List all products with optional filtering."""
    category = request.args.get('category')
    search = request.args.get('search')

    query = Product.query

    if category:
        query = query.filter_by(category=category)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term)
            )
        )

    products = query.all()
    return jsonify([p.to_dict() for p in products])


@app.route('/api/products', methods=['POST'])
def create_product():
    """Create a new product."""
    try:
        data = request.get_json()
        product = Product.from_dict(data)
        db.session.add(product)
        db.session.commit()
        return jsonify(product.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get a single product by ID."""
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update an existing product."""
    product = Product.query.get_or_404(product_id)

    try:
        data = request.get_json()

        # Update allowed fields
        for field in ['name', 'description', 'price', 'quantity', 'category']:
            if field in data:
                setattr(product, field, data[field])

        product.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(product.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product."""
    product = Product.query.get_or_404(product_id)

    try:
        db.session.delete(product)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/products/bulk', methods=['POST'])
def bulk_create():
    """Create multiple products at once."""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({'error': 'Expected a list of products'}), 400

        products = []
        for item in data:
            product = Product.from_dict(item)
            products.append(product)

        db.session.add_all(products)
        db.session.commit()

        return jsonify([p.to_dict() for p in products]), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get product statistics."""
    total = Product.query.count()
    by_category = db.session.query(
        Product.category,
        db.func.count(Product.id).label('count')
    ).group_by(Product.category).all()

    total_value = db.session.query(
        db.func.sum(Product.price * Product.quantity)
    ).scalar() or 0

    return jsonify({
        'total_products': total,
        'by_category': {cat: count for cat, count in by_category if cat},
        'total_inventory_value': float(total_value),
    })


@app.route('/')
def index():
    return """
    <h1>CRUD API Example</h1>
    <h2>Available Endpoints:</h2>
    <ul>
        <li>GET /api/products - List all products</li>
        <li>GET /api/products?category=electronics - Filter by category</li>
        <li>GET /api/products?search=laptop - Search products</li>
        <li>POST /api/products - Create a product</li>
        <li>GET /api/products/1 - Get product by ID</li>
        <li>PUT /api/products/1 - Update product</li>
        <li>DELETE /api/products/1 - Delete product</li>
        <li>POST /api/products/bulk - Bulk create</li>
        <li>GET /api/stats - Product statistics</li>
    </ul>
    <h3>Try it:</h3>
    <pre>
# Create a product
curl -X POST http://localhost:5000/api/products \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Laptop", "price": 999.99, "quantity": 10, "category": "electronics"}'

# List products
curl http://localhost:5000/api/products

# Search products
curl http://localhost:5000/api/products?search=laptop

# Get stats
curl http://localhost:5000/api/stats
    </pre>
    """


# Development data
@app.cli.command()
def seed():
    """Seed the database with sample data."""
    db.create_all()

    products = [
        {'name': 'Laptop', 'description': 'High-performance laptop', 'price': 999.99, 'quantity': 10, 'category': 'electronics'},
        {'name': 'Mouse', 'description': 'Wireless mouse', 'price': 29.99, 'quantity': 50, 'category': 'electronics'},
        {'name': 'Keyboard', 'description': 'Mechanical keyboard', 'price': 79.99, 'quantity': 30, 'category': 'electronics'},
        {'name': 'Desk', 'description': 'Standing desk', 'price': 499.99, 'quantity': 5, 'category': 'furniture'},
        {'name': 'Chair', 'description': 'Ergonomic chair', 'price': 299.99, 'quantity': 15, 'category': 'furniture'},
    ]

    for data in products:
        product = Product.from_dict(data)
        db.session.add(product)

    db.session.commit()
    print(f"Created {len(products)} products")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5003)
