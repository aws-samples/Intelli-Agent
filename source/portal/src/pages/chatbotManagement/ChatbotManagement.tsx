import React, { useEffect, useState, useContext } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Alert,
  Box,
  Button,
  // ButtonDropdown,
  CollectionPreferences,
  ContentLayout,
  FormField,
  Grid,
  Header,
  Input,
  Modal,
  Pagination,
  Select,
  SelectProps,
  SpaceBetween,
  Table,
  Toggle,
} from '@cloudscape-design/components';
import {
  // CreateChatbotResponse,
  ChatbotItem,
  ChatbotResponse,
  // chatbotDetail,
  CreEditChatbotResponse
} from 'src/types';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import { formatTime } from 'src/utils/utils';
import ConfigContext from 'src/context/config-context';
import { EMBEDDING_MODEL_LIST } from 'src/utils/const';

const ChatbotManagement: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<ChatbotItem[]>([]);
  const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const [loadingData, setLoadingData] = useState(false);
  const [allChatbotList, setAllChatbotList] = useState<ChatbotItem[]>([]);
  const [tableChatbotList, setTableChatbotList] = useState<ChatbotItem[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const config = useContext(ConfigContext);

  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [modelList, setModelList] = useState<SelectProps.Option[]>([]);
  // const [chatbotList, setChatbotList] = useState<SelectProps.Option[]>([]);
  const [modelOption, setModelOption] = useState<{label:string;value:string} | null>(
    null,
  );
  // const [chatbotOption, setChatbotOption] = useState<SelectProps.Option | null>(
  //   null,
  // );
  const [chatbotName, setChatbotName] = useState('');
  const [chatbotNameError, setChatbotNameError] = useState('');

  // const [loadingGet, setLoadingGet] = useState(false);
  // validation
  const [modelError, setModelError] = useState('');
  // const [chatbotError, setChatbotError] = useState('');

  const [showDelete, setShowDelete] = useState(false);
  const [useDefaultIndex, setUseDefaultIndex] = useState(true);
  const [qqIndex, setQqIndex] = useState('');
  const [qdIndex, setQdIndex] = useState('');
  const [intentionIndex, setIntentionIndex] = useState('');
  const [qqIndexError, setQqIndexError] = useState('');
  const [qdIndexError, setQdIndexError] = useState('');
  const [intentionIndexError, setIntentionIndexError] = useState('');

  const getModelList = async (type: 'create' | 'edit') => {
    const tempModels:{label: string; value:string}[] =[]
    const BCE_EMBEDDING = [
      {"model_id": config?.embeddingEndpoint || "", "model_name": "BCE_Embedding"},
    ]
    let embedding_models = EMBEDDING_MODEL_LIST

    // Check if config?.embeddingEndpoint starts with "bce-embedding-and-bge-reranker"
    if (config?.embeddingEndpoint?.startsWith("bce-embedding-and-bge-reranker")) {
      embedding_models = [...BCE_EMBEDDING, ...EMBEDDING_MODEL_LIST]
    }

    embedding_models.forEach((item: {model_id: string; model_name: string})=>{
      tempModels.push({
        label: item.model_name,
        value: item.model_id
      })
    })
    setModelList(tempModels)
    if (type === 'create') {
      setModelOption(tempModels[0]);
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

  const deleteChatbot = async () => {
    setLoadingSave(true);
    try {
      await fetchData({
        url: `chatbot-management/chatbots/delete/${selectedItems[0].ChatbotId}`,
        method: 'delete',
      });
      setLoadingSave(false);
      getChatbotList();
      setShowDelete(false);
    } catch (error: unknown) {
      setLoadingSave(false);
    }
  };
  const editChatbot = async ()=>{
    setLoadingSave(true)
    if(!qqIndex?.trim()){
      setQqIndexError(t('validation.requiredIndexName'));
      setLoadingSave(false)
      return;
    }
    if(!qdIndex?.trim()){
      setQdIndexError(t('validation.requiredIndexName'));
      setLoadingSave(false)
      return;
    }
    if(!intentionIndex?.trim()){
      setIntentionIndexError(t('validation.requiredIndexName'));
      setLoadingSave(false)
      return;
    }

    const indexIsValid = await isValidChatbot('edit')

    if(!indexIsValid.result){
      if(indexIsValid.item=="qq") {
        setQqIndexError(t('validation.repeatIndex'))
      } else if(indexIsValid.item=="qd") {
        setQdIndexError(t('validation.repeatIndex'))
      } else if(indexIsValid.item=="intention") {
        setIntentionIndexError(t('validation.repeatIndex'))
      }
      setLoadingSave(false) 
      return;
    }

    const editRes: CreEditChatbotResponse = await fetchData({
      url: `chatbot-management/chatbot/${selectedItems[0].ChatbotId}`,
      method: 'post',
      data: {
         index: {
            qq: qqIndex,
            qd: qdIndex,
            intention: intentionIndex
         }
      }
    });

    if (editRes.Message === 'OK') {
      setShowCreate(false);
      setShowEdit(false);
      getChatbotList();
    }
    setLoadingSave(false);
  }

  const isValidChatbot = async (type:string) =>{
    return await fetchData({
      url: `chatbot-management/check-chatbot`,
      method: 'post',
      data: {
        type,
        chatbotId: chatbotName,
        // groupName: selectedBotOption?.value,
        index: {qq: qqIndex, qd: qdIndex, intention: intentionIndex}, 
        model: modelOption?.value
      },
    });
    // return 
  }
  const createChatbot = async () => {
    // validate model settings
    if (!modelOption?.value?.trim()) {
      setModelError(t('validation.requireModel'));
      return;
    }

    if (!chatbotName?.trim()) {
      setChatbotNameError(t('validation.requireChatbotName'));
      return;
    }

    if(!useDefaultIndex){
      if(!qqIndex?.trim()){
        setQqIndexError(t('validation.requiredIndexName'));
        return;
      }
      if(!qdIndex?.trim()){
        setQdIndexError(t('validation.requiredIndexName'));
        return;
      }
      if(!intentionIndex?.trim()){
        setIntentionIndexError(t('validation.requiredIndexName'));
        return;
      }
    }
    
    setLoadingSave(true);

    const indexIsValid = await isValidChatbot('create')

    if(!indexIsValid.result){
      if(indexIsValid.item=="chatbotName"){
        setChatbotNameError(t('validation.repeatChatbotName'))
      } else if(indexIsValid.item=="qq") {
        setQqIndexError(t('validation.repeatIndex'))
      } else if(indexIsValid.item=="qd") {
        setQdIndexError(t('validation.repeatIndex'))
      } else if(indexIsValid.item=="intention") {
        setIntentionIndexError(t('validation.repeatIndex'))
      }
      setLoadingSave(false) 
      return;
    }
    try {
      // if (type === 'create' && currentChatbot) {
      //   currentChatbot.ChatbotId = createChatbotId;
      // }
      const createRes: CreEditChatbotResponse = await fetchData({
        url: 'chatbot-management/chatbots',
        method: 'post',
        data: {
          chatbotId: chatbotName,
          modelId: modelOption.value,
          modelName: modelOption.label,
          index:{
             qq: qqIndex,
             qd: qdIndex,
             intention: intentionIndex
          }
        },
      });
      // const createRes: CreateChatbotResponse = data;
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

  // const handleChatbotChange = (key: string, subKey: string, value: string) => {
  //   setCurrentChatbot((prevData: any) => ({
  //     ...prevData,
  //     Chatbot: {
  //       ...prevData.Chatbot,
  //       [key]: {
  //         ...prevData.Chatbot[key],
  //         [subKey]: value,
  //       },
  //     },
  //   }));
  // };

  useEffect(() => {
    getChatbotList();
  }, []);

  useEffect(() => {
    setTableChatbotList(
      allChatbotList.slice((currentPage - 1) * pageSize, currentPage * pageSize),
    );
  }, [currentPage, pageSize]);

  useEffect(()=>{
    if(chatbotName?.trim()!==""){
      if(useDefaultIndex){
          setQdIndex(`${chatbotName}-qd-default`);
          setQqIndex(`${chatbotName}-qq-default`);
          setIntentionIndex(`${chatbotName}-intention-default`);
        }}
        
        setQdIndexError('');
        setQqIndexError('');
        setIntentionIndexError('');
      }
    

  ,[chatbotName, useDefaultIndex])
  // useEffect(() => {
  //   if (showCreate && modelOption) {
  //     getChatbotById('create');
  //   }
  // }, [modelOption]);

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
                formatTime(item.LastModifiedTime),
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
                  {/* <ButtonDropdown
                    disabled={selectedItems.length === 0 || selectedItems[0].ChatbotId==="admin"}
                    loading={loadingGet}
                    onItemClick={({ detail }) => {
                      if (detail.id === 'delete') {
                        setShowDelete(true);
                      }
                      if (detail.id === 'edit') {
                        getChatbotById();
                      }
                    }}
                    items={[
                      { text: t('button.edit'), id: 'edit' },
                      { text: t('button.delete'), id: 'delete'},
                    ]}
                  >
                    {t('button.action')}
                  </ButtonDropdown> */}
                  <Button
                    variant="primary"
                    onClick={() => {
                      setChatbotName('')
                      setChatbotNameError('')
                      setQdIndex('')
                      setQqIndex('')
                      setIntentionIndex('')
                      setLoadingSave(false)
                      getModelList('create')
                      setUseDefaultIndex(true)
                      // getChatbotById('create');
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
                      editChatbot();
                    }}
                  >
                    {t('button.save')}
                  </Button>
                ) : (
                  <Button
                    // disabled={loadingGet}
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
          header={showCreate?t('button.createChatbot'):t('button.editChatbot')}
        >
          <SpaceBetween direction="vertical" size="m">
          <FormField
            label={t('chatbotName')}
            
            stretch={true}
            errorText={chatbotNameError}
          >
            <Input
              placeholder={t('chatbotNamePlaceholder')}
              value={chatbotName}
              disabled={showEdit}
              onChange={({ detail }) => {
                setChatbotNameError('');
                setChatbotName(detail.value);
                
              }}
            />
            {/* <Textarea
              rows={1}
              disabled={loadingGet || showEdit}
              value={chatbotOption?.value ?? ''}
              placeholder={'admin'}
              onChange={({ detail }) => {
                setChatbotError('');
                setChatbotOption({ value: detail.value, label: detail.value})
                setCreateChatbotId(detail.value);
              }}
            /> */}
          </FormField>
            <FormField
              label={t('modelName')}
              stretch={true}
              errorText={modelError}
            >
              <Select
                disabled={showEdit}
                onChange={({ detail }:{detail: any}) => {
                  setModelError('');
                  setModelOption(detail.selectedOption);
                }}
                selectedOption={modelOption}
                options={modelList}
                placeholder={t('validation.requireModel')}
                empty={t('noModelFound')}
              />
            </FormField>
            <FormField stretch={true} constraintText={t('indexComment')}>
                  <Toggle
                    onChange={({ detail }) =>
                      {
                        setQdIndexError('');
                        setQqIndexError('');
                        setIntentionIndexError('');
                        // if(chatbotName !==null && chatbotName.trim() !==""){
                        //   setQdIndex(`${chatbotName}-qd-default`);
                        //   setQqIndex(`${chatbotName}-qq-default`);
                        //   setIntentionIndex(`${chatbotName}-intention-default`);
                        // } else {
                        //   setQdIndex('');
                        //   setQqIndex('');
                        //   setIntentionIndex('');
                        // }
                        
                        setUseDefaultIndex(!detail.checked)
                      }
                    }
                    checked={!useDefaultIndex}
                  >
                  {t('customizeIndex')}
                  </Toggle>
                  </FormField>
            {/* <Grid gridDefinition={[{ colspan: 4 }, { colspan: 4 }, { colspan: 4 }]}> */}
              <Grid gridDefinition={[{ colspan: 2 }, { colspan: 10 }]}> 
              <div style={{ height: '100%',display: "flex", alignItems: "center"}}>qq</div>
              <FormField errorText={qqIndexError}>
              <Input
                placeholder={t('indexPlaceholder')}
                disabled={useDefaultIndex}
                onChange={({ detail }) => {
                  setQqIndexError('')
                  setQqIndex(detail.value)
                }}
                value={qqIndex}
              />
              </FormField>
              </Grid>
              
              <Grid gridDefinition={[{ colspan: 2 }, { colspan: 10 }]}> 
              <div style={{ height: '100%',display: "flex", alignItems: "center"}}>qd</div>
              <FormField errorText={qdIndexError}>
              <Input
                placeholder={t('indexPlaceholder')}
                disabled={useDefaultIndex}
                onChange={({ detail }) => {
                  setQdIndexError('')
                  setQdIndex(detail.value)
                }}
                value={qdIndex}
              />
              </FormField>
              </Grid>
              <Grid gridDefinition={[{ colspan: 2 }, { colspan: 10 }]}> 
              <div style={{ height: '100%',display: "flex", alignItems: "center"}}>intention</div>
              <FormField errorText={intentionIndexError}>
              <Input
                placeholder={t('indexPlaceholder')}
                disabled={useDefaultIndex}
                onChange={({ detail }) => {
                  setIntentionIndexError('')
                  setIntentionIndex(detail.value)
                }}
                value={intentionIndex}
              />
              </FormField>
              </Grid>
              <div style={{height:20}}></div>
            {/* </Grid> */}
            {/* <FormField
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
            </FormField> */}
            {/* <Alert type="info">{t('chatbotCreateTips')}</Alert> */}
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
                <li key={item.SortKey}>{item.ChatbotId}</li>
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
