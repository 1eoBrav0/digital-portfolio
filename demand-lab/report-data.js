window.SER_REPORT = {
  "demo": true,
  "events": [
    {
      "id": "WEB-1041",
      "status": "accepted",
      "total_kopecks": 317000
    },
    {
      "id": "WEB-1042",
      "status": "accepted",
      "total_kopecks": 267000
    },
    {
      "id": "WEB-1041",
      "status": "duplicate",
      "total_kopecks": 317000
    },
    {
      "id": "WEB-1043",
      "status": "accepted",
      "total_kopecks": 118000
    },
    {
      "id": "WEB-1042",
      "status": "rejected",
      "reason": "Same ID has conflicting content"
    },
    {
      "id": "WEB-1044",
      "status": "rejected",
      "reason": "Unknown SKU: MISSING"
    },
    {
      "id": "WEB-1045",
      "status": "rejected",
      "reason": "Insufficient stock: CUP-01"
    },
    {
      "id": "WEB-1046",
      "status": "rejected",
      "reason": "Quantity must be an integer from 1 to 10000"
    }
  ],
  "after_timeout": {
    "orders": [
      {
        "id": "WEB-1041",
        "total_kopecks": 317000,
        "status": "retry",
        "attempts": 1
      },
      {
        "id": "WEB-1042",
        "total_kopecks": 267000,
        "status": "retry",
        "attempts": 1
      },
      {
        "id": "WEB-1043",
        "total_kopecks": 118000,
        "status": "retry",
        "attempts": 1
      }
    ],
    "stock": [
      {
        "sku": "BEANS-03",
        "price_kopecks": 89000,
        "available": 12
      },
      {
        "sku": "CUP-01",
        "price_kopecks": 129000,
        "available": 10
      },
      {
        "sku": "FILTER-02",
        "price_kopecks": 59000,
        "available": 17
      }
    ],
    "receiver_count": 0
  },
  "orders": [
    {
      "id": "WEB-1041",
      "total_kopecks": 317000,
      "status": "sent",
      "attempts": 2
    },
    {
      "id": "WEB-1042",
      "total_kopecks": 267000,
      "status": "sent",
      "attempts": 2
    },
    {
      "id": "WEB-1043",
      "total_kopecks": 118000,
      "status": "sent",
      "attempts": 2
    }
  ],
  "stock": [
    {
      "sku": "BEANS-03",
      "price_kopecks": 89000,
      "available": 12
    },
    {
      "sku": "CUP-01",
      "price_kopecks": 129000,
      "available": 10
    },
    {
      "sku": "FILTER-02",
      "price_kopecks": 59000,
      "available": 17
    }
  ],
  "receiver_count": 3
};
