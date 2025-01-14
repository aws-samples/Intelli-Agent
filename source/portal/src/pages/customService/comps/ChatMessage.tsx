import React, { useContext, useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { identity } from 'lodash';
import { Button, Spinner, Textarea } from '@cloudscape-design/components';
import Message from '../../chatbot/components/Message';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import ConfigContext from 'src/context/config-context';
import { DocumentData, MessageDataType, SessionMessage } from 'src/types';
import { useAuth } from 'react-oidc-context';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useAppDispatch, useAppSelector } from 'src/app/hooks';
import { useParams } from 'react-router-dom';
import {
  addDocumentList,
  setCurrentSessionId,
} from 'src/app/slice/cs-workspace';
import { v4 as uuidv4 } from 'uuid';
interface MessageType {
  messageId: string;
  type: 'ai' | 'human';
  message: {
    data: string;
    monitoring: string;
    documentList: DocumentData[];
  };
}

export const ChatMessage: React.FC = () => {
  const { t } = useTranslation();
  const config = useContext(ConfigContext);
  const dispatch = useAppDispatch();
  const csWorkspaceState = useAppSelector((state) => state.csWorkspace);

  const auth = useAuth();
  const fetchData = useAxiosRequest();
  const { id } = useParams();
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [currentAIMessage, setCurrentAIMessage] = useState('');
  const [currentMonitorMessage, setCurrentMonitorMessage] = useState('');
  const [currentAIMessageId, setCurrentAIMessageId] = useState('');
  const [userMessage, setUserMessage] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(false);
  const messageListRef = useRef<HTMLDivElement>(null);
  const [isMessageEnd, setIsMessageEnd] = useState(false);
  const [currentDocumentList, setCurrentDocumentList] = useState<
    DocumentData[]
  >([]);
  const [messages, setMessages] = useState<MessageType[]>([
    {
      messageId: id ?? '',
      type: 'ai',
      message: {
        data: t('welcomeMessage'),
        monitoring: '',
        documentList: [],
      },
    },
  ]);
  const [isTyping] = useState(false);

  const scrollToBottom = (delay = 0) => {
    setTimeout(() => {
      if (messageListRef.current) {
        messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
      }
    }, delay);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    if (aiSpeaking) {
      scrollToBottom(100);
    }
  }, [aiSpeaking, currentAIMessage]);

  const { lastMessage, sendMessage, readyState } = useWebSocket(
    `${config?.websocket}?idToken=${auth.user?.id_token}`,
    {
      onOpen: () => console.log('opened'),
      shouldReconnect: () => true,
    },
  );
  //   const [currentAIMessageId, setCurrentAIMessageId] = useState('');
  //   const [isMessageEnd, setIsMessageEnd] = useState(false);

  const getSessionHistoryById = async (isRefresh = false) => {
    try {
      !isRefresh && setLoadingHistory(true);
      const data = await fetchData({
        url: `sessions/${id}/messages`,
        method: 'get',
        params: {
          page_size: 9999,
          max_items: 9999,
        },
      });
      const sessionMessage: SessionMessage[] = data.Items;

      // Get chatbotId from first message if available
      if (sessionMessage && sessionMessage.length > 0) {
        // const chatbotId = sessionMessage[0].chatbotId;
        // Store chatbotId for use in getWorkspaceList
        // localStorage.setItem(HISTORY_CHATBOT_ID, chatbotId);
      }

      setMessages(
        sessionMessage.map((msg) => {
          let messageContent = msg.content;
          let documentList: DocumentData[] = [];
          // Handle AI images message
          if (msg.role === 'ai' && msg.additional_kwargs?.figure?.length > 0) {
            msg.additional_kwargs.figure.forEach((item) => {
              messageContent += ` \n ![${item.content_type}](/${encodeURIComponent(item.figure_path)})`;
            });
          }
          if (
            msg.role === 'ai' &&
            msg.additional_kwargs?.ref_docs?.length > 0
          ) {
            documentList = msg.additional_kwargs.ref_docs;
          }
          return {
            messageId: msg.messageId,
            type: msg.role,
            message: {
              data: messageContent,
              monitoring: '',
              documentList,
            },
          };
        }),
      );
      setLoadingHistory(false);
    } catch (error) {
      console.error(error);
      return [];
    }
  };

  const handleSendMessage = (autoMessage = '') => {
    setUserMessage('');
    setAiSpeaking(true);
    setCurrentAIMessage('');
    setCurrentMonitorMessage('');
    setIsMessageEnd(false);
    setCurrentDocumentList([]);
    const groupName: string[] = auth?.user?.profile?.['cognito:groups'] as any;
    let message = {
      query: autoMessage || userMessage,
      entry_type: 'common',
      session_id: csWorkspaceState.currentSessionId,
      user_id: auth?.user?.profile?.['cognito:username'] || 'default_user_id',
      chatbot_config: {
        max_rounds_in_memory: 7,
        group_name: groupName?.[0] ?? 'Admin',
        chatbot_id: 'admin',
        chatbot_mode: 'agent',
        use_history: true,
        enable_trace: true,
        use_websearch: true,
        google_api_key: '',
        default_llm_config: {
          model_id: 'anthropic.claude-3-sonnet-20240229-v1:0',
          endpoint_name: '',
          model_kwargs: {
            temperature: 0.01,
            max_tokens: 1000,
          },
        },
        private_knowledge_config: {
          top_k: 5,
          score: 0.4,
        },
        agent_config: {
          only_use_rag_tool: true,
        },
      },
    };

    sendMessage(JSON.stringify(message));
    if (!autoMessage) {
      setMessages((prev) => {
        return [
          ...prev,
          {
            messageId: '',
            type: 'human',
            message: {
              data: userMessage,
              monitoring: '',
              documentList: [],
            },
          },
        ];
      });
      setUserMessage('');
    }
  };

  useEffect(() => {
    if (csWorkspaceState.latestUserMessage) {
      setMessages((prev) => {
        return [
          ...prev,
          {
            messageId: uuidv4(),
            type: 'human',
            message: {
              data: csWorkspaceState.latestUserMessage,
              monitoring: '',
              documentList: [],
            },
          },
        ];
      });
      handleSendMessage(csWorkspaceState.latestUserMessage);
    }
  }, [csWorkspaceState.latestUserMessage]);

  const handleAIMessage = (message: MessageDataType) => {
    console.info('handleAIMessage:', message);
    if (message.message_type === 'START') {
      console.info('message started');
    } else if (message.message_type === 'CHUNK') {
      setCurrentAIMessage((prev) => {
        const newMessage = prev + (message?.message?.content ?? '');
        scrollToBottom(50);
        return newMessage;
      });
    } else if (message.message_type === 'CONTEXT') {
      // handle context message
      if (message.ddb_additional_kwargs?.figure?.length > 0) {
        message.ddb_additional_kwargs.figure.forEach((item) => {
          if (item.content_type === 'md_image') {
            setCurrentAIMessage((prev) => {
              return prev + ` \n ![${item.content_type}](${item.figure_path})`;
            });
          } else {
            setCurrentAIMessage((prev) => {
              return (
                prev +
                ` \n ![${item.content_type}](/${encodeURIComponent(item.figure_path)})`
              );
            });
          }
        });
      }
      // handle ref_docs
      if (message.ref_docs?.length > 0) {
        setCurrentDocumentList(message.ref_docs);
      }
    } else if (message.message_type === 'END') {
      setCurrentAIMessageId(message.message_id);
      setIsMessageEnd(true);
      scrollToBottom(100);
    }
  };

  useEffect(() => {
    if (lastMessage !== null) {
      console.log(lastMessage);
      const message: MessageDataType = JSON.parse(lastMessage.data);
      if (message.message_type === 'MONITOR') {
        setCurrentMonitorMessage((prev) => {
          return prev + (message?.message ?? '');
        });
      } else {
        handleAIMessage(message);
      }
    }
  }, [lastMessage]);

  useEffect(() => {
    if (id) {
      getSessionHistoryById();
      dispatch(setCurrentSessionId(id));
    }
  }, [id]);

  useEffect(() => {
    console.info('csWorkspaceState:', csWorkspaceState);
  }, [csWorkspaceState]);

  const calculateRows = (value: string) => {
    if (!value) return 1; // 空内容时返回 1 行

    // 计算换行符的数量
    const newlines = (value.match(/\n/g) || []).length;

    // 计算每行的字符数（假设每行约 50 个字符）
    const charsPerLine = 50;
    const lines = Math.ceil(value.length / charsPerLine);

    // 取换行符数量和字符换行数量的较大值，并限制在 1-5 行之间
    return Math.max(1, Math.min(5, Math.max(newlines + 1, lines)));
  };

  useEffect(() => {
    if (isMessageEnd) {
      setAiSpeaking(false);
      const documentList =
        currentDocumentList.map((doc) => ({
          ...doc,
          uuid: uuidv4(),
        })) ?? [];
      setMessages((prev) => {
        return [
          ...prev,
          {
            messageId: currentAIMessageId,
            type: 'ai',
            message: {
              data: currentAIMessage,
              monitoring: currentMonitorMessage,
              documentList: documentList,
            },
          },
        ];
      });
      dispatch(addDocumentList(documentList));
    }
  }, [isMessageEnd]);

  if (loadingHistory) {
    return (
      <div className="flex-1 align-center text-center pd-10">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="chat-container mt-10">
      <div className="chat-message flex-v flex-1 gap-10">
        <div className="message-list" ref={messageListRef}>
          {messages.map((msg, index) => (
            <div key={identity(index)}>
              <Message
                showTrace={false}
                type={msg.type}
                message={msg.message}
                documentList={msg.message.documentList}
              />
            </div>
          ))}
          {aiSpeaking && (
            <div>
              <Message
                aiSpeaking={aiSpeaking}
                type="ai"
                showTrace={false}
                message={{
                  data: currentAIMessage,
                  monitoring: currentMonitorMessage,
                }}
                documentList={currentDocumentList}
              />
            </div>
          )}
        </div>
      </div>

      <div className="flex-v gap-10 pd-10">
        <div className="flex gap-5 send-message">
          <div className="flex-1 pr">
            <Textarea
              value={userMessage}
              rows={calculateRows(userMessage)}
              placeholder={t('typeMessage')}
              onChange={({ detail }) => {
                setUserMessage(detail.value);
              }}
              onKeyDown={(e) => {
                if (
                  e.detail.key === 'Enter' &&
                  !e.detail.shiftKey && // 添加 shift+enter 支持换行
                  !aiSpeaking &&
                  readyState === ReadyState.OPEN
                ) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
            />
          </div>
          <div>
            <Button
              disabled={aiSpeaking || readyState !== ReadyState.OPEN}
              onClick={() => {
                handleSendMessage();
              }}
            >
              {t('button.send')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
