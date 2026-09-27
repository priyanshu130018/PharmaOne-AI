import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { api } from "../../api/client.js";

const TOKEN_KEY = "pharmaone_auth_token";
const USER_KEY = "pharmaone_auth_user";

export const login = createAsyncThunk(
  "auth/login",
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const data = await api.login({ email, password });
      if (data?.access_token) {
        localStorage.setItem(TOKEN_KEY, data.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      }
      return data;
    } catch (err) {
      return rejectWithValue(err.message || "Invalid credentials");
    }
  }
);

export const logout = createAsyncThunk("auth/logout", async (_, { dispatch }) => {
  try {
    await api.logout();
  } catch {
    // ignore network errors on logout
  } finally {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    dispatch(clearAuth());
  }
});

export const restoreSession = createAsyncThunk(
  "auth/restoreSession",
  async (_, { rejectWithValue }) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return null;
    try {
      const user = await api.me();
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return { token, user };
    } catch (err) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      return rejectWithValue(err.message || "Session expired");
    }
  }
);

const initialToken = localStorage.getItem(TOKEN_KEY) || null;
let initialUser = null;
try {
  initialUser = JSON.parse(localStorage.getItem(USER_KEY) || "null");
} catch {
  initialUser = null;
}

const authSlice = createSlice({
  name: "auth",
  initialState: {
    token: initialToken,
    user: initialUser,
    isAuthenticated: Boolean(initialToken && initialUser),
    status: "idle",
    error: null,
  },
  reducers: {
    clearAuth: (state) => {
      state.token = null;
      state.user = null;
      state.isAuthenticated = false;
      state.status = "idle";
      state.error = null;
    },
    clearAuthError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.token = action.payload.access_token;
        state.user = action.payload.user;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(login.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload || "Login failed";
        state.isAuthenticated = false;
      })
      // Restore Session
      .addCase(restoreSession.fulfilled, (state, action) => {
        if (action.payload) {
          state.token = action.payload.token;
          state.user = action.payload.user;
          state.isAuthenticated = true;
        } else {
          state.token = null;
          state.user = null;
          state.isAuthenticated = false;
        }
      })
      .addCase(restoreSession.rejected, (state) => {
        state.token = null;
        state.user = null;
        state.isAuthenticated = false;
      });
  },
});

export const { clearAuth, clearAuthError } = authSlice.actions;
export default authSlice.reducer;
