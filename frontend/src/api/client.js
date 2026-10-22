import axios from 'axios';

// backend lambda lives in backend/v1, so cloudfront (aws) and the dev proxy (local)
// both route it under /api/v1
const API_PREFIX = '/api/v1';

// pick the API base url for the current environment:
//  - VITE_API_BASE_URL: explicit override (e.g. pointing straight at a specific server)
//  - VITE_API_URL: set by bin/generate-env.sh (local proxy, http://localhost:3001)
//    and bin/deploy-frontend.sh (aws cloudfront url)
//  - fallback: FastAPI running directly with uvicorn
function resolveBaseURL() {
    const {VITE_API_BASE_URL, VITE_API_URL} = import.meta.env;
    if (VITE_API_BASE_URL) {
        return VITE_API_BASE_URL;
    }
    if (VITE_API_URL) {
        return `${VITE_API_URL.replace(/\/+$/, '')}${API_PREFIX}`;
    }
    return 'http://127.0.0.1:8000';
}

//axios.create is a function that builds a reusable pre-configured client
const apiClient = axios.create({
    baseURL: resolveBaseURL(),
    // repeat list params the way FastAPI reads them: ?status=Open&status=Blocked (not status[]=...)
    paramsSerializer: {indexes: null},
});

apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('accessToken');
    if(token){
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// AuthContext registers a callback here so the client can log the user out
// when the backend rejects their token (expired, invalid, etc.)
let onUnauthorized = null;

export function setUnauthorizedHandler(handler) {
    onUnauthorized = handler;
}

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        // only treat 401s on authenticated requests as a dead session,
        // so a failed login attempt doesn't trigger a logout
        const sentToken = Boolean(error.config?.headers?.Authorization);
        if (error.response?.status === 401 && sentToken && onUnauthorized) {
            onUnauthorized();
        }
        return Promise.reject(error);
    }
);

export default apiClient
