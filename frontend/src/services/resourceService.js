import apiClient from '../api/client.js';

// builds the standard REST calls for one backend resource, e.g. createResource('/facilities')
//   list()            GET    /facilities
//   get(id)           GET    /facilities/{id}
//   create(data)      POST   /facilities
//   update(id, data)  PATCH  /facilities/{id}   (partial update, only changed fields are sent)
//   remove(id)        DELETE /facilities/{id}
// pass overrides to swap any call for a resource that doesn't follow the pattern
export function createResource(path, overrides = {}) {
    return {
        list: (params) => apiClient.get(path, {params}).then((res) => res.data),
        get: (id) => apiClient.get(`${path}/${id}`).then((res) => res.data),
        create: (data) => apiClient.post(path, data).then((res) => res.data),
        update: (id, data) => apiClient.patch(`${path}/${id}`, data).then((res) => res.data),
        remove: (id) => apiClient.delete(`${path}/${id}`),
        ...overrides,
    };
}
