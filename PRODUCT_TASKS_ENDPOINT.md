# 📋 Product Tasks Endpoint - MultiMarket Hub

## Overview

El endpoint `product-tasks` permite consultar el estado de todas las tareas de publicación asíncrona para un producto específico. Proporciona una vista completa de todas las publicaciones realizadas o en proceso para un producto determinado.

## 🔗 Endpoint

### GET `/api/v1/marketplaces/listings/product-tasks/{product_id}/`

Obtiene todas las tareas de publicación asíncrona para un producto específico.

## 📋 Parámetros

### Path Parameters
- `product_id` (required): ID del producto para consultar sus tareas

### Query Parameters
- `status` (optional): Filtrar por estado de tarea
  - Valores válidos: `pending`, `enhancing`, `enhanced`, `publishing`, `published`, `webhook_sent`, `completed`, `failed`
- `marketplace_id` (optional): Filtrar por marketplace específico
- `limit` (optional): Límite de resultados (default: 50, max: 100)
- `offset` (optional): Offset para paginación (default: 0)

## 📤 Respuesta

### Respuesta Exitosa (200 OK)

```json
{
  "product_id": "123",
  "product_title": "iPhone 15 Pro",
  "product_sku": "IPH15P-001",
  "total_tasks": 5,
  "showing": 5,
  "offset": 0,
  "limit": 50,
  "has_more": false,
  "status_summary": {
    "completed": 2,
    "enhancing": 1,
    "failed": 1,
    "publishing": 1
  },
  "marketplace_summary": {
    "MercadoLibre": 3,
    "Amazon": 2
  },
  "tasks": [
    {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "product": 123,
      "marketplace": 456,
      "status": "completed",
      "current_step": "Process completed successfully",
      "steps_completed": ["enhancement", "publication", "webhook"],
      "total_steps": 4,
      "progress_percentage": 75.0,
      "enhancement_retries": 0,
      "publication_retries": 1,
      "webhook_retries": 0,
      "enhancement_result": {
        "success": true,
        "enhanced_description": "AI-enhanced product description...",
        "keywords": ["smartphone", "apple", "premium"]
      },
      "publication_result": {
        "success": true,
        "marketplace_id": "MLM123456789",
        "listing_url": "https://mercadolibre.com/item/MLM123456789"
      },
      "webhook_result": {
        "status_code": 200,
        "response": "OK"
      },
      "error_details": {},
      "started_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T10:05:30Z",
      "product_title": "iPhone 15 Pro",
      "product_sku": "IPH15P-001",
      "marketplace_name": "MercadoLibre"
    },
    {
      "task_id": "660f9511-f3ac-52e5-b827-557766551111",
      "product": 123,
      "marketplace": 789,
      "status": "failed",
      "current_step": "Failed during publication",
      "steps_completed": ["enhancement"],
      "total_steps": 4,
      "progress_percentage": 25.0,
      "enhancement_retries": 0,
      "publication_retries": 3,
      "webhook_retries": 0,
      "enhancement_result": {
        "success": true,
        "enhanced_description": "AI-enhanced product description..."
      },
      "publication_result": {},
      "webhook_result": {},
      "error_details": {
        "step": "publication",
        "error": "Invalid product category for marketplace",
        "marketplace_response": {
          "error_code": "INVALID_CATEGORY",
          "message": "Category 'Electronics' not found"
        },
        "retries": 3
      },
      "started_at": "2024-01-15T11:00:00Z",
      "completed_at": null,
      "product_title": "iPhone 15 Pro",
      "product_sku": "IPH15P-001",
      "marketplace_name": "Amazon"
    }
  ]
}
```

### Respuesta de Error

#### Producto No Encontrado (404 Not Found)
```json
{
  "error": "Product with id 999 not found"
}
```

#### Marketplace No Encontrado (404 Not Found)
```json
{
  "error": "Marketplace with id 999 not found"
}
```

#### Sin Autenticación (403 Forbidden)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

## 📊 Campos de Respuesta

### Información del Producto
- `product_id`: ID del producto
- `product_title`: Título del producto
- `product_sku`: SKU del producto

### Información de Paginación
- `total_tasks`: Total de tareas encontradas
- `showing`: Número de tareas mostradas en esta página
- `offset`: Offset actual
- `limit`: Límite aplicado
- `has_more`: Indica si hay más resultados disponibles

### Resúmenes
- `status_summary`: Conteo de tareas por estado
- `marketplace_summary`: Conteo de tareas por marketplace

### Información de Tareas
Cada tarea incluye:
- `task_id`: ID único de la tarea
- `status`: Estado actual de la tarea
- `current_step`: Descripción del paso actual
- `progress_percentage`: Porcentaje de progreso (0-100)
- `steps_completed`: Lista de pasos completados
- `*_retries`: Número de reintentos por cada paso
- `*_result`: Resultados de cada paso del proceso
- `error_details`: Detalles del error (solo si status = "failed")
- `started_at`: Timestamp de inicio
- `completed_at`: Timestamp de finalización (null si no ha terminado)

## 🔍 Ejemplos de Uso

### 1. Obtener Todas las Tareas de un Producto

```bash
curl -X GET "http://localhost:8000/api/v1/marketplaces/listings/product-tasks/123/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Filtrar por Estado

```bash
curl -X GET "http://localhost:8000/api/v1/marketplaces/listings/product-tasks/123/?status=completed" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Filtrar por Marketplace

```bash
curl -X GET "http://localhost:8000/api/v1/marketplaces/listings/product-tasks/123/?marketplace_id=456" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Paginación

```bash
curl -X GET "http://localhost:8000/api/v1/marketplaces/listings/product-tasks/123/?limit=10&offset=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Filtros Combinados

```bash
curl -X GET "http://localhost:8000/api/v1/marketplaces/listings/product-tasks/123/?status=failed&marketplace_id=456&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🐍 Ejemplo con Python

```python
import requests

# Configuración
base_url = "http://localhost:8000"
product_id = 123
headers = {"Authorization": "Bearer YOUR_TOKEN"}

# Obtener todas las tareas
response = requests.get(
    f"{base_url}/api/v1/marketplaces/listings/product-tasks/{product_id}/",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    
    print(f"Producto: {data['product_title']} ({data['product_sku']})")
    print(f"Total de tareas: {data['total_tasks']}")
    
    # Mostrar resumen por estado
    print("\nResumen por estado:")
    for status, count in data['status_summary'].items():
        print(f"  {status}: {count}")
    
    # Mostrar resumen por marketplace
    print("\nResumen por marketplace:")
    for marketplace, count in data['marketplace_summary'].items():
        print(f"  {marketplace}: {count}")
    
    # Mostrar tareas
    print("\nTareas:")
    for task in data['tasks']:
        print(f"  {task['task_id']}: {task['status']} ({task['progress_percentage']:.1f}%)")
        if task['error_details']:
            print(f"    Error: {task['error_details'].get('error', 'Unknown error')}")

else:
    print(f"Error: {response.status_code} - {response.text}")
```

## 📈 Casos de Uso

### 1. Dashboard de Producto
Mostrar el estado de todas las publicaciones de un producto en un dashboard administrativo.

### 2. Monitoreo de Errores
Identificar productos con tareas fallidas para tomar acciones correctivas.

### 3. Análisis de Performance
Analizar tiempos de publicación y tasas de éxito por marketplace.

### 4. Auditoría
Mantener un registro completo de todas las actividades de publicación de un producto.

### 5. Notificaciones
Crear alertas basadas en el estado de las tareas de productos específicos.

## 🔧 Integración con Frontend

### React/JavaScript Example

```javascript
const ProductTasksComponent = ({ productId }) => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    status: '',
    marketplace_id: '',
    limit: 20,
    offset: 0
  });

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams(
        Object.entries(filters).filter(([_, value]) => value !== '')
      );
      
      const response = await fetch(
        `/api/v1/marketplaces/listings/product-tasks/${productId}/?${params}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
      }
    } catch (error) {
      console.error('Error fetching tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [productId, filters]);

  return (
    <div className="product-tasks">
      <h2>Tareas de Publicación - {tasks.product_title}</h2>
      
      {/* Filtros */}
      <div className="filters">
        <select 
          value={filters.status} 
          onChange={(e) => setFilters({...filters, status: e.target.value})}
        >
          <option value="">Todos los estados</option>
          <option value="completed">Completado</option>
          <option value="failed">Fallido</option>
          <option value="enhancing">Mejorando</option>
        </select>
      </div>
      
      {/* Resumen */}
      {tasks.status_summary && (
        <div className="summary">
          <h3>Resumen por Estado</h3>
          {Object.entries(tasks.status_summary).map(([status, count]) => (
            <span key={status} className={`badge ${status}`}>
              {status}: {count}
            </span>
          ))}
        </div>
      )}
      
      {/* Lista de tareas */}
      <div className="tasks-list">
        {tasks.tasks?.map(task => (
          <div key={task.task_id} className={`task-item ${task.status}`}>
            <div className="task-header">
              <span className="task-id">{task.task_id}</span>
              <span className="marketplace">{task.marketplace_name}</span>
              <span className="status">{task.status}</span>
            </div>
            <div className="task-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{width: `${task.progress_percentage}%`}}
                />
              </div>
              <span>{task.progress_percentage.toFixed(1)}%</span>
            </div>
            <div className="task-details">
              <p>{task.current_step}</p>
              {task.error_details && (
                <div className="error-details">
                  <strong>Error:</strong> {task.error_details.error}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {/* Paginación */}
      {tasks.has_more && (
        <button 
          onClick={() => setFilters({
            ...filters, 
            offset: filters.offset + filters.limit
          })}
        >
          Cargar más
        </button>
      )}
    </div>
  );
};
```

## 🎯 Beneficios

### Para Desarrolladores
- **API Consistente**: Sigue los mismos patrones que otros endpoints
- **Filtrado Flexible**: Múltiples opciones de filtrado y paginación
- **Información Completa**: Todos los detalles necesarios en una sola llamada

### Para Usuarios
- **Visibilidad Total**: Vista completa del estado de publicaciones
- **Información Detallada**: Progreso, errores y resultados específicos
- **Histórico Completo**: Registro de todas las actividades de publicación

### Para el Sistema
- **Performance Optimizada**: Consultas eficientes con paginación
- **Escalable**: Maneja grandes volúmenes de tareas
- **Mantenible**: Código limpio y bien estructurado

Este endpoint complementa perfectamente el flujo asíncrono de publicación, proporcionando la visibilidad necesaria para monitorear y gestionar las publicaciones de productos de manera efectiva.