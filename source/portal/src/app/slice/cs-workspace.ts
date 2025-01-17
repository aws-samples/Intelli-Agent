import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { ChatSessionType, DocumentData } from 'src/types';

// Define a type for the slice state
interface CSWorkspaceState {
  currentSessionId: string;
  documentList: DocumentData[];
  activeDocumentId: string;
  latestUserMessage: string;
  currentUser: ChatSessionType | null;
  autoSendMessage: string;
}

// Define the initial state using that type
const initialState: CSWorkspaceState = {
  currentSessionId: '',
  documentList: [],
  activeDocumentId: '',
  latestUserMessage: '',
  currentUser: null,
  autoSendMessage: '',
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
    setLatestUserMessage: (state, action: PayloadAction<string>) => {
      state.latestUserMessage = action.payload;
    },
    setCurrentUser: (state, action: PayloadAction<ChatSessionType | null>) => {
      state.currentUser = action.payload;
    },
    setAutoSendMessage: (state, action: PayloadAction<string>) => {
      state.autoSendMessage = action.payload;
    },
    clearAutoSendMessage: (state) => {
      state.autoSendMessage = '';
    },
  },
});

export const {
  setCurrentSessionId,
  addDocumentList,
  clearDocumentList,
  setActiveDocumentId,
  setLatestUserMessage,
  setCurrentUser,
  setAutoSendMessage,
  clearAutoSendMessage,
} = csWorkspaceSlice.actions;

export default csWorkspaceSlice.reducer;
