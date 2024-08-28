import React, { useEffect, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Alert,
  Box,
  Button,
  ButtonDropdown,
  CollectionPreferences,
  ContentLayout,
  FormField,
  Header,
  Modal,
  Pagination,
  Select,
  SelectProps,
  SpaceBetween,
  Spinner,
  Table,
  Tabs,
  Textarea,
} from '@cloudscape-design/components';
import {
  CreateChatbotResponse,
  GetChatbotResponse,
  ChatbotItem
} from 'src/types';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import { formatTime } from 'src/utils/utils';

const ChatbotManagement: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<ChatbotItem[]>([]);
  const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const [loadingData] = useState(false);
  const [allChatbotList] = useState<ChatbotItem[]>([]);
  const [tableChatbotList, setTableChatbotList] = useState<ChatbotItem[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [currentChatbot, setCurrentChatbot] = useState<GetChatbotResponse>();
  const [modelList, setModelList] = useState<SelectProps.Option[]>([]);
  const [chatbotList, setChatbotList] = useState<SelectProps.Option[]>([]);
  const [modelOption, setModelOption] = useState<SelectProps.Option | null>(
    null,
  );
  const [chatbotOption, setChatbotOption] = useState<SelectProps.Option | null>(
    null,
  );

  const [loadingGet, setLoadingGet] = useState(false);
  // validation
  const [modelError, setModelError] = useState('');
  const [chatbotError, setChatbotError] = useState('');

  const [showDelete, setShowDelete] = useState(false);

  const getModelList = async (type: 'create' | 'edit') => {
    setLoadingGet(true);
    try {
      const data = await fetchData({
        url: 'prompt-management/models',
        method: 'get',
      });
      const items: string[] = data;
      const getModels = items.map((item) => {
        return {
          label: item,
          value: item,
        };
      });
      setModelList(getModels);
      if (type === 'create') {
        setModelOption(getModels[0]);
      }
    } catch (error: unknown) {
      setLoadingGet(false);
    }
  };

  const getChatbotList = async () => {
    setLoadingGet(true);
    try {
      const data = await fetchData({
        url: 'chatbot-management/chatbots',
        method: 'get',
      });
      const items: string[] = data.chatbot_ids;
      const getChatbots = items.map((item) => {
        return {
          label: item,
          value: item,
        };
      });
      setChatbotList(getChatbots);
      setChatbotOption(getChatbots[0]);
    } catch (error: unknown) {
      setLoadingGet(false);
    }
  };

  const getPromptById = async (type: 'create' | 'edit') => {
    setLoadingGet(true);
    let requestUrl = `prompt-management/prompts/${modelOption?.value}/common`;
    if (type === 'edit') {
      requestUrl = `prompt-management/prompts/${selectedItems[0].ModelId}/common`;
      setModelOption({
        label: selectedItems[0].ModelId,
        value: selectedItems[0].ModelId,
      });
    }
    try {
      const data: GetChatbotResponse = await fetchData({
        url: requestUrl,
        method: 'get',
      });
      setLoadingGet(false);
      setCurrentChatbot(data);
      if (type === 'edit') {
        setShowEdit(true);
      }
    } catch (error: unknown) {
      console.info('error:', error);
      setLoadingGet(false);
    }
  };

  const deletePrompt = async () => {
    setLoadingSave(true);
    try {
      await fetchData({
        url: `prompt-management/prompts/${selectedItems[0].ModelId}/common`,
        method: 'delete',
      });
      setLoadingSave(false);
      getChatbotList();
      setShowDelete(false);
    } catch (error: unknown) {
      setLoadingSave(false);
    }
  };

  const createPrompt = async () => {
    // validate model settings
    if (!modelOption?.value?.trim()) {
      setModelError(t('validation.requireModel'));
      return;
    }
    setLoadingSave(true);
    try {
      const data = await fetchData({
        url: 'prompt-management/prompts',
        method: 'post',
        data: currentChatbot,
      });
      const createRes: CreateChatbotResponse = data;
      if (createRes.Message === 'OK') {
        setShowCreate(false);
        setShowEdit(false);
        getChatbotList();
      }
      setLoadingSave(false);
    } catch (error: unknown) {
      setLoadingSave(false);
    }
  };

  const handlePromptChange = (key: string, subKey: string, value: string) => {
    setCurrentChatbot((prevData: any) => ({
      ...prevData,
      Prompt: {
        ...prevData.Prompt,
        [key]: {
          ...prevData.Prompt[key],
          [subKey]: value,
        },
      },
    }));
  };

  useEffect(() => {
    getChatbotList();
  }, []);

  useEffect(() => {
    setTableChatbotList(
      allChatbotList.slice((currentPage - 1) * pageSize, currentPage * pageSize),
    );
  }, [currentPage, pageSize]);

  useEffect(() => {
    if (showCreate && modelOption) {
      getPromptById('create');
    }
  }, [modelOption]);

  return (
    <CommonLayout
      activeHref="/prompts"
      breadCrumbs={[
        {
          text: t('name'),
          href: '/',
        },
        {
          text: t('prompt'),
          href: '/prompts',
        },
      ]}
    >
      <ContentLayout>
        <Table
          selectionType="single"
          resizableColumns
          loading={loadingData}
          onSelectionChange={({ detail }) =>
            setSelectedItems(detail.selectedItems)
          }
          selectedItems={selectedItems}
          ariaLabels={{
            allItemsSelectionLabel: ({ selectedItems }) =>
              `${selectedItems.length} ${
                selectedItems.length === 1 ? t('item') : t('items')
              } ${t('selected')}`,
          }}
          columnDefinitions={[
            {
              id: 'modelId',
              header: t('modelName'),
              cell: (item: ChatbotItem) => item.ModelId,
              isRowHeader: true,
            },
            // {
            //   id: 'updateBy',
            //   header: t('updateBy'),
            //   cell: (item: ChatbotItem) => item.LastModifiedBy,
            // },
            {
              id: 'updateTime',
              header: t('updateTime'),
              cell: (item: ChatbotItem) =>
                formatTime(parseInt(item.LastModifiedTime) * 1000),
            },
          ]}
          items={tableChatbotList}
          loadingText={t('loadingData')}
          trackBy="uuid"
          empty={
            <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
              <SpaceBetween size="m">
                <b>{t('noData')}</b>
              </SpaceBetween>
            </Box>
          }
          pagination={
            <Pagination
              disabled={loadingData}
              currentPageIndex={currentPage}
              pagesCount={Math.ceil(allChatbotList.length / pageSize)}
              onChange={({ detail }) => setCurrentPage(detail.currentPageIndex)}
            />
          }
          preferences={
            <CollectionPreferences
              title={t('preferences')}
              confirmLabel={t('button.confirm')}
              cancelLabel={t('button.cancel')}
              onConfirm={({ detail }) => {
                setPageSize(detail.pageSize ?? 10);
                setCurrentPage(1);
              }}
              preferences={{
                pageSize: pageSize,
              }}
              pageSizePreference={{
                title: t('pageSize'),
                options: [10, 20, 50, 100].map((size) => ({
                  value: size,
                  label: `${size} ${t('items')}`,
                })),
              }}
            />
          }
          header={
            <Header
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    iconName="refresh"
                    loading={loadingData}
                    onClick={() => {
                      getChatbotList();
                    }}
                  />
                  <ButtonDropdown
                    disabled={selectedItems.length === 0}
                    loading={loadingGet}
                    onItemClick={({ detail }) => {
                      if (detail.id === 'delete') {
                        setShowDelete(true);
                      }
                      if (detail.id === 'edit') {
                        getPromptById('edit');
                      }
                    }}
                    items={[
                      { text: t('button.edit'), id: 'edit' },
                      { text: t('button.delete'), id: 'delete' },
                    ]}
                  >
                    {t('button.action')}
                  </ButtonDropdown>
                  <Button
                    variant="primary"
                    onClick={() => {
                      getModelList('create');
                      getChatbotList();
                      setShowCreate(true);
                    }}
                  >
                    {t('button.createPrompt')}
                  </Button>
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${allChatbotList.length})`
                  : `(${allChatbotList.length})`
              }
            >
              {t('prompts')}
            </Header>
          }
        />
        <Modal
          onDismiss={() => {
            setShowCreate(false);
            setShowEdit(false);
          }}
          visible={showCreate || showEdit}
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="link"
                  onClick={() => {
                    setShowCreate(false);
                    setShowEdit(false);
                  }}
                >
                  {t('button.cancel')}
                </Button>
                {showEdit ? (
                  <Button
                    loading={loadingSave}
                    variant="primary"
                    onClick={() => {
                      createPrompt();
                    }}
                  >
                    {t('button.save')}
                  </Button>
                ) : (
                  <Button
                    disabled={loadingGet}
                    loading={loadingSave}
                    variant="primary"
                    onClick={() => {
                      createPrompt();
                    }}
                  >
                    {t('button.createPrompt')}
                  </Button>
                )}
              </SpaceBetween>
            </Box>
          }
          header={t('button.createPrompt')}
        >
          <SpaceBetween direction="vertical" size="xs">
            <FormField
              label={t('chatbotName')}
              stretch={true}
              errorText={chatbotError}
            >
              <Select
                disabled={loadingGet || showEdit}
                onChange={({ detail }) => {
                  setChatbotError('');
                  setChatbotOption(detail.selectedOption);
                }}
                selectedOption={chatbotOption}
                options={chatbotList}
                placeholder={t('validation.requireChatbot')}
                empty={t('noChatbotFound')}
              />
            </FormField>
            <FormField
              label={t('modelName')}
              stretch={true}
              errorText={modelError}
            >
              <Select
                disabled={loadingGet || showEdit}
                onChange={({ detail }) => {
                  setModelError('');
                  setModelOption(detail.selectedOption);
                }}
                selectedOption={modelOption}
                options={modelList}
                placeholder={t('validation.requireModel')}
                empty={t('noModelFound')}
              />
            </FormField>
            <FormField
              label={t('prompts')}
              stretch={true}
              errorText={chatbotError}
            >
              {loadingGet ? (
                <Spinner />
              ) : (
                <Tabs
                  tabs={
                    currentChatbot?.Chatbot
                      ? Object.keys(currentChatbot?.Chatbot).map((key) => ({
                          label: key,
                          id: key,
                          content: (
                            <>
                              {Object.keys(currentChatbot?.Chatbot[key]).map(
                                (subKey) => (
                                  <FormField key={subKey} label={subKey}>
                                    <Textarea
                                      rows={5}
                                      placeholder={t(
                                        'validation.requirePrompt',
                                      )}
                                      value={currentChatbot.Chatbot[key][subKey]}
                                      onChange={({ detail }) => {
                                        setChatbotError('');
                                        handlePromptChange(
                                          key,
                                          subKey,
                                          detail.value,
                                        );
                                      }}
                                    />
                                  </FormField>
                                ),
                              )}
                            </>
                          ),
                        }))
                      : []
                  }
                />
              )}
            </FormField>
            <Alert type="info">{t('promptCreateTips')}</Alert>
          </SpaceBetween>
        </Modal>

        <Modal
          onDismiss={() => setShowDelete(false)}
          visible={showDelete}
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="link"
                  onClick={() => {
                    setShowDelete(false);
                  }}
                >
                  {t('button.cancel')}
                </Button>
                <Button
                  loading={loadingSave}
                  variant="primary"
                  onClick={() => {
                    deletePrompt();
                  }}
                >
                  {t('button.delete')}
                </Button>
              </SpaceBetween>
            </Box>
          }
          header={t('alert')}
        >
          <Box variant="h4">{t('deleteTips')}</Box>
          <div className="selected-items-list">
            <ul className="gap-5 flex-v">
              {selectedItems.map((item) => (
                <li key={item.SortKey}>{item.ModelId}</li>
              ))}
            </ul>
          </div>
          <Alert type="warning">{t('promptDeleteTips')}</Alert>
        </Modal>
      </ContentLayout>
    </CommonLayout>
  );
};

export default ChatbotManagement;
