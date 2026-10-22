// factory for the standard CRUD calls of one REST resource. services/index.js creates one per
// backend resource, and hooks/useResource.js consumes the resulting object
import apiClient from '../api/client.js';

// builds the standard REST calls for one backend resource, e.g. createResource('/facilities')
//   list()            GET    /facilities
//   listPage(params)  GET    /facilities?limit=&offset=&sort=&q=  -> {rows, total}  (total from the X-Total-Count header)
//   get(id)           GET    /facilities/{id}
//   create(data)      POST   /facilities
//   update(id, data)  PATCH  /facilities/{id}   (partial update, only changed fields are sent)
//   remove(id)        DELETE /facilities/{id}
// pass overrides to swap any call for a resource that doesn't follow the pattern
// every call resolves to the response body, except remove() (the backend answers 204 No Content)
export function createResource(path, overrides = {}) {
    return {
        list: (params) => apiClient.get(path, {params}).then((res) => res.data),
        listPage: (params) => apiClient.get(path, {params}).then((res) => ({
            rows: res.data,
            // axios lower-cases header names. falls back to the row count if the header is missing
            // (e.g. not exposed by CORS, or an endpoint that doesn't page)
            total: Number(res.headers['x-total-count'] ?? res.data.length),
        })),
        get: (id) => apiClient.get(`${path}/${id}`).then((res) => res.data),
        create: (data) => apiClient.post(path, data).then((res) => res.data),
        update: (id, data) => apiClient.patch(`${path}/${id}`, data).then((res) => res.data),
        remove: (id) => apiClient.delete(`${path}/${id}`),
        ...overrides,
    };
}
