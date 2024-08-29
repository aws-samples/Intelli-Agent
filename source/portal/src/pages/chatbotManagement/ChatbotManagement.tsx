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
  ChatbotItem,
  ChatbotResponse
} from 'src/types';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import { formatTime } from 'src/utils/utils';

const ChatbotManagement: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<ChatbotItem[]>([]);
  const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const [loadingData, setLoadingData] = useState(false);
  const [allChatbotList, setAllChatbotList] = useState<ChatbotItem[]>([]);
  const [tableChatbotList, setTableChatbotList] = useState<ChatbotItem[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [currentChatbot, setCurrentChatbot] = useState<GetChatbotResponse>();
  const [modelList, setModelList] = useState<SelectProps.Option[]>([]);
  // const [chatbotList, setChatbotList] = useState<SelectProps.Option[]>([]);
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
        url: 'chatbot-management/embeddings',
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
    setLoadingData(true);
    setSelectedItems([]);
    const params = {
      max_items: 9999,
      page_size: 9999,
    };
    try {
      const data = await fetchData({
        url: 'chatbot-management/chatbots',
        method: 'get',
        params,
      });
      const items: ChatbotResponse = data;
      const preSortItem = items.Items.map((chatbot) => {
        return {
          ...chatbot,
          uuid: chatbot.ChatbotId,
        };
      });
      setAllChatbotList(preSortItem);
      setTableChatbotList(preSortItem.slice(0, pageSize));
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  };

  const getChatbotById = async (type: 'create' | 'edit') => {
    setLoadingGet(true);
    let requestUrl = `chatbot-management/chatbots/create`;
    if (type === 'edit') {
      requestUrl = `chatbot-management/chatbots/edit`;
      setChatbotOption({
        label: selectedItems[0].ChatbotId,
        value: selectedItems[0].ChatbotId,
      });
      setModelOption({
        label: selectedItems[0].ModelName,
        value: selectedItems[0].ModelName,
      });
    }
    try {
      let chatbotIdParam = '';
      if (selectedItems.length > 0) {
        chatbotIdParam = selectedItems[0].ChatbotId;
      } else {
        chatbotIdParam = 'admin';
      }
      const data: GetChatbotResponse = await fetchData({
        url: requestUrl,
        method: 'get',
        params: {
          chatbotId: chatbotIdParam,
        },
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

  const deleteChatbot = async () => {
    setLoadingSave(true);
    try {
      await fetchData({
        url: `chatbot-management/chatbots/common`,
        method: 'delete',
      });
      setLoadingSave(false);
      getChatbotList();
      setShowDelete(false);
    } catch (error: unknown) {
      setLoadingSave(false);
    }
  };

  const createChatbot = async () => {
    // validate model settings
    if (!modelOption?.value?.trim()) {
      setModelError(t('validation.requireModel'));
      return;
    }
    setLoadingSave(true);
    try {
      const data = await fetchData({
        url: 'chatbot-management/chatbots',
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

  const handleChatbotChange = (key: string, subKey: string, value: string) => {
    setCurrentChatbot((prevData: any) => ({
      ...prevData,
      Chatbot: {
        ...prevData.Chatbot,
        [key]: {
          ...prevData.Chatbot[key],
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
      getChatbotById('create');
    }
  }, [modelOption]);

  return (
    <CommonLayout
      activeHref="/chatbots"
      breadCrumbs={[
        {
          text: t('name'),
          href: '/',
        },
        {
          text: t('chatbot'),
          href: '/chatbots',
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
              id: 'chatbotId',
              header: t('chatbotName'),
              cell: (item: ChatbotItem) => item.ChatbotId,
              isRowHeader: true,
            },
            {
              id: 'modelId',
              header: t('modelName'),
              cell: (item: ChatbotItem) => item.ModelName,
              isRowHeader: true,
            },
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
                        getChatbotById('edit');
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
                      getChatbotById('create');
                      setShowCreate(true);
                    }}
                  >
                    {t('button.createChatbot')}
                  </Button>
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${allChatbotList.length})`
                  : `(${allChatbotList.length})`
              }
            >
              {t('chatbots')}
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
                      createChatbot();
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
                      createChatbot();
                    }}
                  >
                    {t('button.createChatbot')}
                  </Button>
                )}
              </SpaceBetween>
            </Box>
          }
          header={t('button.createChatbot')}
        >
          <SpaceBetween direction="vertical" size="xs">
          <FormField
            label={t('chatbotName')}
            stretch={true}
            errorText={chatbotError}
          >
            <Textarea
              rows={1}
              value={chatbotOption?.value ?? ''}
              placeholder={'admin'}
              onChange={({ detail }) => {
                setChatbotError('');
                setChatbotOption({ value: detail.value, label: detail.value})
                // setCurrentChatbot((prevData: any) => ({
                //   ...prevData,
                //   ChatbotId: detail.value,
                // }));
              }}
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
              label={t('chatbots')}
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
                                        'validation.requireChatbot',
                                      )}
                                      value={currentChatbot.Chatbot[key][subKey]}
                                      onChange={({ detail }) => {
                                        setChatbotError('');
                                        handleChatbotChange(
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
            <Alert type="info">{t('chatbotCreateTips')}</Alert>
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
                    deleteChatbot();
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
                <li key={item.SortKey}>{item.ModelName}</li>
              ))}
            </ul>
          </div>
          <Alert type="warning">{t('chatbotDeleteTips')}</Alert>
        </Modal>
      </ContentLayout>
    </CommonLayout>
  );
};

export default ChatbotManagement;
