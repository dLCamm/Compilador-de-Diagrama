const API_URL = "http://localhost:8000";

async function requestBackend(endpoint, options = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || `Error HTTP ${response.status}`);
  }

  return data;
}

export function compilarDiagrama(payload) {
  return requestBackend("/compilar", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function traducirC(payload) {
  return requestBackend("/traducir/c", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function traducirAssembler(payload) {
  return requestBackend("/traducir/assembler", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function obtenerUltimoC() {
  return requestBackend("/ultimo/c");
}

export function obtenerUltimoAssembler() {
  return requestBackend("/ultimo/assembler");
}

export function obtenerUltimoEcho() {
  return requestBackend("/ultimo/echo");
}
