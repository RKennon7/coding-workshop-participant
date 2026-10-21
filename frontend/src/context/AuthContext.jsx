import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import apiClient, { setUnauthorizedHandler } from "../api/client";
import { registerAccount } from "../services/index.js";

/**
 * Global auth state using React's context API
 */

const AuthContext = createContext(null);

// extract + decode user payload from JWT, returns null if the token is malformed
function decodeToken(token){
    try {
        // JWTs are base64url encoded, convert to regular base64 before decoding
        const payloadSegment = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(payloadSegment));
        // note: atob means ASCII to Binary
    } catch {
        return null;
    }
}

// exp claim is in seconds since epoch, Date.now() is in ms
function isExpired(payload){
    return !payload || (payload.exp && payload.exp * 1000 <= Date.now());
}

// read the stored token on startup, discarding it if it has already expired
function loadStoredToken(){
    const stored = localStorage.getItem('accessToken');
    if (stored && isExpired(decodeToken(stored))) {
        localStorage.removeItem('accessToken');
        return null;
    }
    return stored;
}

// AuthProvider wraps the app and manages authentication state
export function AuthProvider({children}) {
    // init token state from local storage
    const [token, setToken] = useState(loadStoredToken);
    // lets the login screen explain why the user was sent back to it
    const [sessionExpired, setSessionExpired] = useState(false);

    // decode JWT into user obj and cache results to prevent re-decoding token
    // str on every re-render. only runs when token changes
    // payload: {sub: username, uid: user id, role, exp}
    const user = useMemo(() => (token ? decodeToken(token): null), [token]);

    const storeToken = (accessToken) => {
        localStorage.setItem('accessToken', accessToken);
        setSessionExpired(false);
        setToken(accessToken);
    };

    // username can be either the username or the email
    const login = async (username, password) => {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await apiClient.post('/auth/token', formData, {
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        });
        storeToken(response.data.access_token);
    }

    // claims the account an admin created for this email; the backend returns a token, so this also logs in
    const register = async (email, password) => {
        const data = await registerAccount({email, password});
        storeToken(data.access_token);
    };

    const logout = useCallback(() => {
        localStorage.removeItem('accessToken');
        setToken(null);
    }, []);

    const expireSession = useCallback(() => {
        setSessionExpired(true);
        logout();
    }, [logout]);

    // log out automatically once the token's exp time is reached
    useEffect(() => {
        if (!user?.exp) {
            return;
        }
        const msUntilExpiry = user.exp * 1000 - Date.now();
        const timer = setTimeout(expireSession, Math.max(msUntilExpiry, 0));
        return () => clearTimeout(timer);
    }, [user, expireSession]);

    // log out if the backend rejects the token (401) before the timer fires
    useEffect(() => {
        setUnauthorizedHandler(expireSession);
        return () => setUnauthorizedHandler(null);
    }, [expireSession]);

    // bundles auth state variables and action functions into a single object to define
    // the exact interface exposed to components that are consuming this context
    const value = {token, user, isAuthenticated: Boolean(token), sessionExpired, login, register, logout};

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// custom react hook to expose AuthContext to any component
// simplifies context usage in child react components
export function useAuth() {
    const context = useContext(AuthContext);
    if (context === null){
        throw new Error('useAuth must be used within AuthProvider')
    }
    return context;
}
