import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { DocumentData } from 'src/types';

// Define a type for the slice state
interface CSWorkspaceState {
  currentSessionId: string;
  documentList: DocumentData[];
  activeDocumentId: string;
}

// Define the initial state using that type
const initialState: CSWorkspaceState = {
  currentSessionId: '',
  documentList: [],
  activeDocumentId: '',
};

export const csWorkspaceSlice = createSlice({
  name: 'csWorkspace',
  // `createSlice` will infer the state type from the `initialState` argument
  initialState,
  reducers: {
    setCurrentSessionId: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
    addDocumentList: (state, action: PayloadAction<DocumentData[]>) => {
      state.documentList = [...state.documentList, ...action.payload];
    },
    clearDocumentList: (state) => {
      state.documentList = [];
    },
    setActiveDocumentId: (state, action: PayloadAction<string>) => {
      state.activeDocumentId = action.payload;
    },
  },
});

export const {
  setCurrentSessionId,
  addDocumentList,
  clearDocumentList,
  setActiveDocumentId,
} = csWorkspaceSlice.actions;

export default csWorkspaceSlice.reducer;
