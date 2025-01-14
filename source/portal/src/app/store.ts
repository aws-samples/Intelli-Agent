import { configureStore } from '@reduxjs/toolkit';
import csWorkspaceReducer from './slice/cs-workspace';

export const store = configureStore({
  reducer: {
    csWorkspace: csWorkspaceReducer,
  },
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch;
