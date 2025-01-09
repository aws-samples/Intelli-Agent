import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

// Define a type for the slice state
interface CSWorkspaceState {
  currentSessionId: string;
}

// Define the initial state using that type
const initialState: CSWorkspaceState = {
  currentSessionId: '',
};

export const csWorkspaceSlice = createSlice({
  name: 'csWorkspace',
  // `createSlice` will infer the state type from the `initialState` argument
  initialState,
  reducers: {
    setCurrentSessionId: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
  },
});

export const { setCurrentSessionId } = csWorkspaceSlice.actions;

export default csWorkspaceSlice.reducer;
