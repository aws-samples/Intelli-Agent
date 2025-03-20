import React, { useEffect, useState, useContext } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Box,
  Button,
  ButtonDropdown,
  CollectionPreferences,
  ContentLayout,
  FormField,
  Grid,
  Header,
  Input,
  Pagination,
  Select,
  SelectProps,
  SpaceBetween,
  Table,
  Toggle,
  Link,
} from '@cloudscape-design/components';
import {
  ChatbotDetailResponse,
  ChatbotResponse,
  CreEditChatbotResponse,
  SelectedOption,
} from 'src/types';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import { formatTime, isChinaRegion } from 'src/utils/utils';
import ConfigContext, { Config } from 'src/context/config-context';
import {
  API_ENDPOINT,
  API_KEY_ARN,
  BEDROCK_API_EMBEDDING_MODEL_LIST,
  BEDROCK_RERANK_MODEL_LIST,
  BEDROCK_VLM_MODEL_LIST,
  EMBEDDING_MODEL_LIST,
  INDEX_TYPE_OPTIONS,
  OPENAI_API_EMBEDDING_MODEL_LIST,
  ROUTES,
} from 'src/utils/const';
import { useNavigate } from 'react-router-dom';
import RightModal from '../right-modal';
import minus from 'src/assets/images/minus.png';
import plus from 'src/assets/images/plus.png';
import './style.scss';

interface INDEX_TYPE {
  name: string;
  type: string;
  tag: string;
  desc: string;
  errText: string;
}

const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return url.startsWith('http://') || url.startsWith('https://');
  } catch {
    return false;
  }
};

const isValidArn = (arn: string): boolean => {
  // AWS Global and China ARN patterns
  // arn:aws:secretsmanager:region:account-id:secret:name
  // arn:aws-cn:secretsmanager:region:account-id:secret:name
  const arnPattern =
    /^arn:aws(?:-cn)?:secretsmanager:[a-z0-9-]+:\d{12}:secret:.+$/;
  return arnPattern.test(arn);
};

const isValidChatbotName = (
  name: string,
): { valid: boolean; message: string } => {
  // Check if name starts with _ or -
  if (name.startsWith('_') || name.startsWith('-')) {
    return { valid: false, message: 'validation.noStartWithUnderscoreOrDash' };
  }

  // Check for non-standard English characters (allows a-z, 0-9, underscore, hyphen, and period)
  if (!/^[a-z0-9_\-\.]+$/.test(name)) {
    return { valid: false, message: 'validation.onlyStandardEnglishAllowed' };
  }

  return { valid: true, message: '' };
};

const ChatbotManagement: React.FC = () => {
  const { t } = useTranslation();
  const INITIAL_INDEX_LIST: INDEX_TYPE[] = [
    {
      name: '',
      type: 'qq',
      tag: '',
      desc: t('defaultIndexDesc'),
      errText: '',
    },
    {
      name: '',
      type: 'qd',
      tag: '',
      desc: t('defaultIndexDesc'),
      errText: '',
    },
    {
      name: '',
      type: 'intention',
      tag: '',
      desc: t('defaultIndexDesc'),
      errText: '',
    },
  ];
  const [selectedItems, setSelectedItems] = useState<ChatbotDetailResponse[]>([]);
  const fetchData = useAxiosRequest();

  const [loadingData, setLoadingData] = useState(false);
  const [allChatbotList, setAllChatbotList] = useState<ChatbotDetailResponse[]>([]);
  const [tableChatbotList, setTableChatbotList] = useState<ChatbotDetailResponse[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const config: Config | null = useContext(ConfigContext);
  console.log('config');
  console.log(config);
  const localApiEndpoint = localStorage.getItem(API_ENDPOINT);
  const localApiKeyArn = localStorage.getItem(API_KEY_ARN);
  const embeddingModelTypeList = [
    ...(isChinaRegion(config) ? [] : [{ label: 'Bedrock', value: 'Bedrock' }]),
    {
      label: 'Bedrock API',
      value: 'Bedrock API',
    },
    {
      label: 'OpenAI API',
      value: 'OpenAI API',
    },
    { label: 'SageMaker', value: 'SageMaker' }
  ];

  const rerankModelTypeList = [
    ...(isChinaRegion(config) ? [] : [{ label: 'Bedrock', value: 'Bedrock' }]),
    { label: 'SageMaker', value: 'SageMaker' }
  ];

  const vlmModelTypeList = [
    ...(isChinaRegion(config) ? [] : [{ label: 'Bedrock', value: 'Bedrock' }]),
    ...(isChinaRegion(config)
      ? [{ label: 'SageMaker', value: 'SageMaker' }]
      : []),
  ];

  const [embeddingModelType, setEmbeddingModelType] = useState<SelectProps.Option>(
    embeddingModelTypeList[0],
  );
  const [rerankModelType, setRerankModelType] = useState<SelectProps.Option>(
    rerankModelTypeList[0],
  );

  const [vlmModelType, setVlmModelType] = useState<SelectProps.Option>(
    vlmModelTypeList[0],
  );
  
  const [embeddingApiEndpointError, setEmbeddingApiEndpointError] = useState('');
  const [embeddingApiKeyArnError, setEmbeddingApiKeyArnError] = useState('');
  const [embeddingApiEndpoint, setEmbeddingApiEndpoint] = useState(localApiEndpoint ?? '');
  const [embeddingApiKeyArn, setEmbeddingApiKeyArn] = useState(localApiKeyArn ?? '');


  const [rerankApiEndpointError, setRerankApiEndpointError] = useState('');
  const [rerankApiKeyArnError, setRerankApiKeyArnError] = useState('');
  const [rerankApiEndpoint, setRerankApiEndpoint] = useState(localApiEndpoint ?? '');
  const [rerankApiKeyArn, setRerankApiKeyArn] = useState(localApiKeyArn ?? '');

  const [vlmApiEndpointError, setVlmApiEndpointError] = useState('');
  const [vlmApiKeyArnError, setVlmApiKeyArnError] = useState('');
  const [vlmApiEndpoint, setVlmApiEndpoint] = useState(localApiEndpoint ?? '');
  const [vlmApiKeyArn, setVlmApiKeyArn] = useState(localApiKeyArn ?? '');

  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  // const [loadingEmbeddingModels, setLoadingEmbeddingModels] = useState(false);
  // const [loadingRerankModels, setLoadingRerankModels] = useState(false);
  // const [loadingVlmModels, setLoadingVlmModels] = useState(false);
  const [embeddingModelList, setEmbeddingModelList] = useState<SelectProps.Option[]>([]);
  const [embeddingModelOption, setEmbeddingModelOption] = useState<{
    label: string;
    value: string;
  } | null>(null);
  const [rerankModelList, setRerankModelList] = useState<SelectProps.Option[]>([]);
  const [rerankModelOption, setRerankModelOption] = useState<{
    label: string;
    value: string;
  } | null>(null);
  const [vlmModelList, setVlmModelList] = useState<SelectProps.Option[]>([]);
  const [vlmModelOption, setVlmModelOption] = useState<{
    label: string;
    value: string;
  } | null>(null);
  const [chatbotName, setChatbotName] = useState('');
  const [chatbotNameError, setChatbotNameError] = useState('');
  // validation
  const [embeddingModelError, setEmbeddingModelError] = useState('');
  const [rerankModelError, setRerankModelError] = useState('');
  const [vlmModelError, setVlmModelError] = useState('');
  const [useDefaultIndex, setUseDefaultIndex] = useState(true);
  const [indexList, setIndexList] = useState(INITIAL_INDEX_LIST);
  const [endpoints, setEndpoints] = useState<{label: string, value: string}[]>([])
  

  const indexTypeOption: SelectedOption[] = INDEX_TYPE_OPTIONS;
  const navigate = useNavigate();

  useEffect(() => {
    const fetchEndpoints = async () =>{
      const tempModels: { label: string; value: string }[] = [];
      const data = await fetchData({
        url: 'model-management/endpoints',
        method: 'get'
      });
      data.endpoints.forEach((endpoint: any) => {
        tempModels.push({
          label: endpoint.endpoint_name,
          value: endpoint.endpoint_name,
        });
      });
      setEndpoints(tempModels)
    }
    fetchEndpoints();
  },[])

  useEffect(() => {
    const tempModels: { label: string; value: string }[] = [];
    if (embeddingModelType.value === 'Bedrock API') {
      BEDROCK_API_EMBEDDING_MODEL_LIST.forEach(
        (item: { model_id: string; model_name: string }) => {
          tempModels.push({
            label: item.model_name,
            value: item.model_id,
          });
        },
      );
    } else if (embeddingModelType.value === 'OpenAI API') {
      OPENAI_API_EMBEDDING_MODEL_LIST.forEach(
        (item: { model_id: string; model_name: string }) => {
          tempModels.push({
            label: item.model_name,
            value: item.model_id,
          });
        },
      );
    } else if (embeddingModelType.value === 'Bedrock') {
      EMBEDDING_MODEL_LIST.forEach(
        (item: { model_id: string; model_name: string }) => {
          tempModels.push({
            label: item.model_name,
            value: item.model_id,
          });
        },
      );
      setEmbeddingApiEndpoint('');
      setEmbeddingApiKeyArn('');
    } else if (embeddingModelType.value === 'SageMaker') {
      // TODO
      // setLoadingEmbeddingModels(true);
      setEmbeddingModelList(endpoints)
      setEmbeddingModelOption(endpoints[0]);
      // setLoadingEmbeddingModels(false);
      return
    }
    setEmbeddingModelList(tempModels);
    setEmbeddingModelOption(tempModels[0]);
  }, [embeddingModelType]);


  useEffect(() => {
    const tempModels: { label: string; value: string }[] = [];
    if (rerankModelType.value === 'Bedrock') {
      BEDROCK_RERANK_MODEL_LIST.forEach(
        (item: { model_id: string; model_name: string }) => {
          tempModels.push({
            label: item.model_name,
            value: item.model_id,
          });
        },
      );
      setRerankApiEndpoint('');
      setRerankApiKeyArn('');
    } else if (rerankModelType.value === 'SageMaker') {
      setRerankModelList(endpoints)
      setRerankModelOption(endpoints[0]);
      return
    }
    setRerankModelList(tempModels);
    setRerankModelOption(tempModels[0]);
  }, [rerankModelType]);

  useEffect(() => {
    const tempModels: { label: string; value: string }[] = [];
    if (vlmModelType.value === 'Bedrock') {
      BEDROCK_VLM_MODEL_LIST.forEach(
        (item: { model_id: string; model_name: string }) => {
          tempModels.push({
            label: item.model_name,
            value: item.model_id,
          });
        },
      );
      setVlmApiEndpoint('');
      setVlmApiKeyArn('');
    } else if (rerankModelType.value === 'SageMaker') {
      setVlmModelList(endpoints)
      setVlmModelOption(endpoints[0]);
      return
    }
    setVlmModelList(tempModels);
    setVlmModelOption(tempModels[0]);
  }, [vlmModelType]);

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
      const preSortItem = items.items.map((chatbot) => {
        return {
          ...chatbot,
          uuid: chatbot.chatbotId,
        };
      });
      setAllChatbotList(preSortItem);
      setTableChatbotList(preSortItem.slice(0, pageSize));
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  };

  const removeIndex = (removedIndex: number) => {
    setIndexList((prevIndexList) =>
      prevIndexList.filter((_, index) => index !== removedIndex),
    );
  };

  const addIndex = () => {
    setIndexList((prevIndexList) => [
      ...prevIndexList,
      {
        name: '',
        type: 'qq',
        desc: t('defaultIndexDesc'),
        tag: '',
        errText: '',
      },
    ]);
  };

  const isValidChatbot = async (type: string) => {
    return await fetchData({
      url: 'chatbot-management/check-chatbot',
      method: 'post',
      data: {
        type,
        chatbotId: chatbotName,
        // groupName: selectedBotOption?.value,
        index: genBotIndexCheck(),
        model: embeddingModelOption?.value,
      },
    });
    // return
  };

  const genBotIndexCheck = () => {
    let index: any = {};
    indexList.map((item: INDEX_TYPE) => {
      if (!index[item.type]) {
        index[item.type] = '';
      }
      index[item.type] += item.name + ',';
    });
    for (let type in index) {
      index[type] = index[type].slice(0, -1);
    }

    return index;
  };

  const genBotIndexCreate = () => {
    let index: any = {};
    indexList.map((item: INDEX_TYPE) => {
      if (!index[item.type]) {
        index[item.type] = {};
      }
      index[item.type][item.name] = item.desc;
    });
    return index;
  };
  const createChatbot = async () => {
    let staticCheck = true;
    // validate model settings
    if (!embeddingModelOption?.value?.trim()) {
      setEmbeddingModelError(t('validation.requireModel'));
      return;
    }

    if (!rerankModelOption?.value?.trim()) {
      setRerankModelError(t('validation.requireModel'));
      return;
    }

    if (!vlmModelOption?.value?.trim()) {
      setVlmModelError(t('validation.requireModel'));
      return;
    }

    if (!chatbotName?.trim()) {
      setChatbotNameError(t('validation.requireChatbotName'));
      return;
    }

    // Replace the uppercase validation with the new comprehensive validation
    const nameValidation = isValidChatbotName(chatbotName);
    if (!nameValidation.valid) {
      setChatbotNameError(t(nameValidation.message));
      return;
    }

    if (
      !embeddingApiEndpoint?.trim() &&
      (embeddingModelType?.value === 'Bedrock API' || embeddingModelType.value === 'OpenAI API')
    ) {
      setEmbeddingApiEndpointError(t('validation.requireApiEndpoint'));
      return;
    }

    if (
      !embeddingApiKeyArn?.trim() &&
      (embeddingModelType.value === 'Bedrock API' || embeddingModelType.value === 'OpenAI API')
    ) {
      setEmbeddingApiKeyArnError(t('validation.requireApiKeyArn'));
      return;
    }

    if (
      !rerankApiEndpoint?.trim() &&
      (rerankModelType?.value === 'Bedrock API' || rerankModelType?.value === 'OpenAI API')
    ) {
      setRerankApiEndpointError(t('validation.requireApiEndpoint'));
      return;
    }

    if (
      !rerankApiKeyArn?.trim() &&
      (rerankModelType.value === 'Bedrock API' || rerankModelType.value === 'OpenAI API')
    ) {
      setRerankApiKeyArnError(t('validation.requireApiKeyArn'));
      return;
    }

    if (
      !vlmApiEndpoint?.trim() &&
      (vlmModelType?.value === 'Bedrock API' || vlmModelType?.value === 'OpenAI API')
    ) {
      setVlmApiEndpointError(t('validation.requireApiEndpoint'));
      return;
    }

    if (
      !vlmApiKeyArn?.trim() &&
      (vlmModelType.value === 'Bedrock API' || vlmModelType.value === 'OpenAI API')
    ) {
      setVlmApiKeyArnError(t('validation.requireApiKeyArn'));
      return;
    }

    if (!useDefaultIndex) {
      const validIndexNames: string[] = [];
      setIndexList((prevIndexList) =>
        prevIndexList.map((item) => {
          if (item.name?.trim().length === 0) {
            staticCheck = false;
            return {
              ...item,
              errText: t('validation.requiredIndexName'),
            };
          } else if (validIndexNames.includes(item.name)) {
            staticCheck = false;
            return {
              ...item,
              errText: t('validation.repeatedIndexName'),
            };
          } else {
            validIndexNames.push(item.name);
            return item;
          }
        }),
      );
      if (!staticCheck) return;
    }

    setLoadingSave(true);

    const indexIsValid = await isValidChatbot('create');

    if (!indexIsValid.result) {
      if (indexIsValid.item == 'chatbotName') {
        setChatbotNameError(t('validation.repeatChatbotName'));
      } else {
        setIndexList((prevIndexList) =>
          prevIndexList.map((item) => {
            return item.name == indexIsValid.item
              ? {
                  ...item,
                  errText:
                    indexIsValid.reason == 1
                      ? t('validation.repeatIndex')
                      : t('validation.indexValid'),
                }
              : item;
          }),
        );
      }
      setLoadingSave(false);
      return;
    }
    // bce-embedding-base_v1
    try {
      const createRes: CreEditChatbotResponse = await fetchData({
        url: 'chatbot-management/chatbots',
        method: 'post',
        data: {
          chatbotId: chatbotName,
          embeddingModelInfo: {
            "modelProvider": embeddingModelType.value,
            "modelId": embeddingModelType.value === "SageMaker" ? "bce-embedding-base_v1":embeddingModelOption.value,
            "modelEndpoint": embeddingModelType.value === "SageMaker" ? embeddingModelOption.value:"",
            "baseUrl": "",
            "apiKeyArn": ""
          },
          rerankModelInfo: {
            "modelProvider": rerankModelType.value,
            "modelId": rerankModelType.value === "SageMaker" ? "bce-embedding-base_v1":rerankModelOption.value,
            "modelEndpoint": rerankModelType.value === "SageMaker" ? rerankModelOption.value:"",
            "baseUrl": "",
            "apiKeyArn": ""
          },
          vlmModelInfo: {
            "modelProvider": vlmModelType.value,
            "modelId": vlmModelType.value === "SageMaker" ? "bce-embedding-base_v1":vlmModelOption.value,
            "modelEndpoint": vlmModelType.value === "SageMaker" ? vlmModelOption.value:"",
            "baseUrl": "",
            "apiKeyArn": ""
          },
          index: genBotIndexCreate()
        },
      });
      // const createRes: CreateChatbotResponse = data;
      if (createRes.message === 'OK') {
        setShowCreate(false);
        setShowEdit(false);
        getChatbotList();
      }
      setLoadingSave(false);
    } catch (error: unknown) {
      setLoadingSave(false);
    }
  };

  useEffect(() => {
    getChatbotList();
  }, []);

  useEffect(() => {
    setTableChatbotList(
      allChatbotList.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
      ),
    );
  }, [currentPage, pageSize]);

  useEffect(() => {
    if (chatbotName?.trim() !== '') {
      if (useDefaultIndex) {
        setIndexList(
          INITIAL_INDEX_LIST.map((item) => ({
            ...item,
            name: `${chatbotName}-${item.type}-default`,
          })),
        );
      }
    } else {
      setIndexList(INITIAL_INDEX_LIST);
    }
  }, [chatbotName, useDefaultIndex]);

  const changeIndexName = (value: string, index: number) => {
    setIndexList((prevIndexList) =>
      prevIndexList.map((item, i) => {
        if (i === index) {
          return {
            ...item,
            name: value,
            errText: '',
          };
        } else {
          return item;
        }
      }),
    );
  };

  const changeIndexType = (value: string, index: number) => {
    setIndexList((prevIndexList) =>
      prevIndexList.map((item, i) => {
        if (i === index) {
          return {
            ...item,
            type: value,
          };
        } else {
          return item;
        }
      }),
    );
  };

  const changeIndexDesc = (value: string, index: number) => {
    setIndexList((prevIndexList) =>
      prevIndexList.map((item, i) => {
        if (i === index) {
          return {
            ...item,
            desc: value,
          };
        } else {
          return item;
        }
      }),
    );
  };

  return (
    <CommonLayout
      activeHref={ROUTES.Chatbot}
      breadCrumbs={[
        {
          text: t('name'),
          href: ROUTES.Home,
        },
        {
          text: t('chatbot'),
          href: ROUTES.Chatbot,
        },
      ]}
    >
      <ContentLayout>
        <div style={{ marginTop: '25px' }} />
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
              cell: (item: ChatbotDetailResponse) => item.chatbotId,
              isRowHeader: true,
            },
            {
              id: 'modelProvider',
              header: t('modelProvider'),
              cell: (item: ChatbotDetailResponse) => item.embeddingModel.modelProvider,
              isRowHeader: true,
            },
            {
              id: 'modelId',
              header: t('modelName'),
              cell: (item: ChatbotDetailResponse) => item.embeddingModel.modelId,
              isRowHeader: true,
            },
            {
              id: 'updateTime',
              header: t('updateTime'),
              cell: (item: ChatbotDetailResponse) => formatTime(item.updateTime),
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
                    onItemClick={({ detail }) => {
                      // if (detail.id === 'delete') {
                      //   setShowDelete(true);
                      // }
                      if (detail.id === 'edit') {
                        // getChatbotById();
                        navigate(
                          `/chatbot/detail/${selectedItems[0].chatbotId}`,
                        );
                      }
                    }}
                    items={[
                      { text: t('button.edit'), id: 'edit' },
                      // { text: t('button.delete'), id: 'delete'},
                    ]}
                  >
                    {t('button.action')}
                  </ButtonDropdown>
                  <Button
                    variant="primary"
                    onClick={() => {
                      setChatbotName('');
                      setChatbotNameError('');
                      setEmbeddingApiKeyArnError('');
                      setEmbeddingApiEndpointError('');
                      setRerankApiKeyArnError('');
                      setRerankApiEndpointError('');
                      setVlmApiKeyArnError('');
                      setVlmApiEndpointError('');
                      setLoadingSave(false);
                      setUseDefaultIndex(true);
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
        <RightModal
          setShowModal={setShowCreate}
          showModal={showCreate}
          header={t('button.createChatbot')}
          showFolderIcon={false}
        >
          <div className="create-chatbot-modal">
            <SpaceBetween direction="vertical" size="xl">
              <FormField
                label={t('chatbotName')}
                stretch={true}
                description={t('chatbotNameDesc')}
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
              </FormField>
              <FormField
                label={t('embeddingModel')}
                stretch={true}
                description={t('embeddingModelDesc')}
              >
               {embeddingModelType.value === 'Bedrock API' ||
                embeddingModelType.value === 'OpenAI API' ? (<>
                <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                // label={t('modelProvider')}
                stretch={true}
                description={t('modelProvider')}
              >
                <Select
                  options={embeddingModelTypeList}
                  selectedOption={embeddingModelType}
                  onChange={({ detail }) => {
                    setEmbeddingModelType(detail.selectedOption);
                  }}
                />
              </FormField>
                  <FormField
                    // label={t('modelName')}
                    stretch={true}
                    errorText={t(embeddingModelError)}
                    description={t('modelName')}
                  >
                    <Select
                      disabled={showEdit}
                      onChange={({ detail }: { detail: any }) => {
                        setEmbeddingModelError('');
                        setEmbeddingModelOption(detail.selectedOption);
                      }}
                      selectedOption={embeddingModelOption}
                      options={embeddingModelList}
                      placeholder={t('validation.requireModel')}
                      empty={t('noModelFound')}
                    />
                  </FormField>
                  </Grid>
                  <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                    // label={t('apiEndpoint')}
                    stretch={true}
                    errorText={t(embeddingApiEndpointError)}
                    description={t('apiEndpoint')}
                  >
                    <Input
                      value={embeddingApiEndpoint}
                      onChange={({ detail }) => {
                        const value = detail.value;
                        if (value === '' || isValidUrl(value)) {
                          setEmbeddingApiEndpointError('');
                        } else {
                          setEmbeddingApiEndpointError(
                            'Invalid url, please type in a valid HTTPS or HTTP url',
                          );
                        }
                        setEmbeddingApiEndpoint(value);
                      }}
                      placeholder="https://api.example.com/v1"
                    />
                  </FormField>
                  <FormField
                    // label={t('apiKeyArn')}
                    stretch={true}
                    errorText={t(embeddingApiKeyArnError)}
                    description={t('apiKeyArn')}
                  >
                    <Input
                      value={embeddingApiKeyArn}
                      onChange={({ detail }) => {
                        const value = detail.value;
                        if (value === '' || isValidArn(value)) {
                          setEmbeddingApiKeyArnError('');
                        } else {
                          setEmbeddingApiKeyArnError(
                            'Invalid ARN, please type in a valid secret ARN from AWS Secrets Manager',
                          );
                        }
                        setEmbeddingApiKeyArn(value);
                      }}
                      placeholder="arn:aws:secretsmanager:region:account:secret:name"
                    />
                  </FormField>
                </Grid>
                </>
              ) : (
                <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                // label={t('modelProvider')}
                stretch={true}
                description={t('modelProvider')}
              >
                <Select
                  options={embeddingModelTypeList}
                  selectedOption={embeddingModelType}
                  onChange={({ detail }) => {
                    setEmbeddingModelType(detail.selectedOption);
                  }}
                />
              </FormField>
                <FormField
                  description={embeddingModelType.value === "SageMaker" ? t('endpoint'): t('modelName')}
                  // label={t('embeddingModelName')}
                  stretch={true}
                  errorText={embeddingModelError}
                >
                  <Select
                    disabled={showEdit}
                    onChange={({ detail }: { detail: any }) => {
                      setEmbeddingModelError('');
                      setEmbeddingModelOption(detail.selectedOption);
                    }}
                    loadingText={t('loadingEp')}
                    selectedOption={embeddingModelOption}
                    options={embeddingModelList}
                    placeholder={t('validation.requireModel')}
                    empty={t('noModelFound')}
                  />
                </FormField>
                </Grid>
              )}
              </FormField>

              <FormField
                label={t('rerankModel')}
                stretch={true}
                description={t('rerankModelDesc')}
              >
                {rerankModelType.value === 'Bedrock API' ||
                rerankModelType.value === 'OpenAI API' ? (<>
                <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                // label={t('modelProvider')}
                stretch={true}
                description={t('modelProvider')}
              >
                <Select
                  options={rerankModelTypeList}
                  selectedOption={rerankModelType}
                  onChange={({ detail }) => {
                    setRerankModelType(detail.selectedOption);
                  }}
                />
              </FormField>
                  <FormField
                    // label={t('modelName')}
                    stretch={true}
                    errorText={t(rerankModelError)}
                    description={t('modelName')}
                  >
                    <Select
                      disabled={showEdit}
                      onChange={({ detail }: { detail: any }) => {
                        setRerankModelError('');
                        setRerankModelOption(detail.selectedOption);
                      }}
                      selectedOption={rerankModelOption}
                      options={rerankModelList}
                      placeholder={t('validation.requireModel')}
                      empty={t('noModelFound')}
                    />
                  </FormField>
                  </Grid>
                  <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                    // label={t('apiEndpoint')}
                    stretch={true}
                    errorText={t(rerankApiEndpointError)}
                    description={t('apiEndpoint')}
                  >
                    <Input
                      value={rerankApiEndpoint}
                      onChange={({ detail }) => {
                        const value = detail.value;
                        if (value === '' || isValidUrl(value)) {
                          setRerankApiEndpointError('');
                        } else {
                          setRerankApiEndpointError(
                            'Invalid url, please type in a valid HTTPS or HTTP url',
                          );
                        }
                        setRerankApiEndpoint(value);
                      }}
                      placeholder="https://api.example.com/v1"
                    />
                  </FormField>
                  <FormField
                    // label={t('apiKeyArn')}
                    stretch={true}
                    errorText={t(rerankApiKeyArnError)}
                    description={t('apiKeyArn')}
                  >
                    <Input
                      value={rerankApiKeyArn}
                      onChange={({ detail }) => {
                        const value = detail.value;
                        if (value === '' || isValidArn(value)) {
                          setRerankApiKeyArnError('');
                        } else {
                          setRerankApiKeyArnError(
                            'Invalid ARN, please type in a valid secret ARN from AWS Secrets Manager',
                          );
                        }
                        setRerankApiKeyArn(value);
                      }}
                      placeholder="arn:aws:secretsmanager:region:account:secret:name"
                    />
                  </FormField>
                </Grid>
                </>
              ) : (
                <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                // label={t('modelProvider')}
                stretch={true}
                description={t('modelProvider')}
              >
                <Select
                  options={rerankModelTypeList}
                  selectedOption={rerankModelType}
                  onChange={({ detail }) => {
                    setRerankModelType(detail.selectedOption);
                  }}
                />
              </FormField>
                <FormField
                  description={rerankModelType.value === "SageMaker" ? t('endpoint'): t('modelName')}
                  // label={t('embeddingModelName')}
                  stretch={true}
                  errorText={rerankModelError}
                >
                  <Select
                    disabled={showEdit}
                    onChange={({ detail }: { detail: any }) => {
                      setRerankModelError('');
                      setRerankModelOption(detail.selectedOption);
                    }}
                    loadingText={t('loadingEp')}
                    selectedOption={rerankModelOption}
                    options={rerankModelList}
                    placeholder={t('validation.requireModel')}
                    empty={t('noModelFound')}
                  />
                </FormField>
                </Grid>
              )}
              </FormField>

              <FormField
                label={t('vlmModel')}
                stretch={true}
                description={t('vlmModelDesc')}
              >
                {vlmModelType.value === 'Bedrock API' ||
                vlmModelType.value === 'OpenAI API' ? (<>
                <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                // label={t('modelProvider')}
                stretch={true}
                description={t('modelProvider')}
              >
                <Select
                  options={vlmModelTypeList}
                  selectedOption={vlmModelType}
                  onChange={({ detail }) => {
                    setVlmModelType(detail.selectedOption);
                  }}
                />
              </FormField>
                  <FormField
                    // label={t('modelName')}
                    stretch={true}
                    errorText={t(vlmModelError)}
                    description={t('modelName')}
                  >
                    <Select
                      disabled={showEdit}
                      onChange={({ detail }: { detail: any }) => {
                        setVlmModelError('');
                        setVlmModelOption(detail.selectedOption);
                      }}
                      selectedOption={vlmModelOption}
                      options={vlmModelList}
                      placeholder={t('validation.requireModel')}
                      empty={t('noModelFound')}
                    />
                  </FormField>
                  </Grid>
                  <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                    // label={t('apiEndpoint')}
                    stretch={true}
                    errorText={t(vlmApiEndpointError)}
                    description={t('apiEndpoint')}
                  >
                    <Input
                      value={vlmApiEndpoint}
                      onChange={({ detail }) => {
                        const value = detail.value;
                        if (value === '' || isValidUrl(value)) {
                          setVlmApiEndpointError('');
                        } else {
                          setVlmApiEndpointError(
                            'Invalid url, please type in a valid HTTPS or HTTP url',
                          );
                        }
                        setVlmApiEndpoint(value);
                      }}
                      placeholder="https://api.example.com/v1"
                    />
                  </FormField>
                  <FormField
                    // label={t('apiKeyArn')}
                    stretch={true}
                    errorText={t(vlmApiKeyArnError)}
                    description={t('apiKeyArn')}
                  >
                    <Input
                      value={vlmApiKeyArn}
                      onChange={({ detail }) => {
                        const value = detail.value;
                        if (value === '' || isValidArn(value)) {
                          setVlmApiKeyArnError('');
                        } else {
                          setVlmApiKeyArnError(
                            'Invalid ARN, please type in a valid secret ARN from AWS Secrets Manager',
                          );
                        }
                        setVlmApiKeyArn(value);
                      }}
                      placeholder="arn:aws:secretsmanager:region:account:secret:name"
                    />
                  </FormField>
                </Grid>
                </>
              ) : (
                <Grid gridDefinition={[{colspan:4}, {colspan:8}]}>
                  <FormField
                // label={t('modelProvider')}
                stretch={true}
                description={t('modelProvider')}
              >
                <Select
                  options={vlmModelTypeList}
                  selectedOption={vlmModelType}
                  onChange={({ detail }) => {
                    setVlmModelType(detail.selectedOption);
                  }}
                />
              </FormField>
                <FormField
                  description={vlmModelType.value === "SageMaker" ? t('endpoint'): t('modelName')}
                  stretch={true}
                  errorText={vlmModelError}
                >
                  <Select
                    disabled={showEdit}
                    onChange={({ detail }: { detail: any }) => {
                      setVlmModelError('');
                      setVlmModelOption(detail.selectedOption);
                    }}
                    loadingText={t('loadingEp')}
                    selectedOption={vlmModelOption}
                    options={vlmModelList}
                    placeholder={t('validation.requireModel')}
                    empty={t('noModelFound')}
                  />
                </FormField>
                </Grid>
              )}
              </FormField>

              <FormField stretch={true} label={t('indexManagement')}>
                <Toggle
                  onChange={({ detail }) => {
                    // setQdIndexError('');
                    // setQqIndexError('');
                    // setIntentionIndexError('');
                    setUseDefaultIndex(!detail.checked);
                  }}
                  checked={!useDefaultIndex}
                >
                  {t('customizeIndex')}
                </Toggle>
              </FormField>
              {/* <div> */}
              {indexList != null && indexList.length > 0 ? (
                <>
                  <Grid
                    gridDefinition={[
                      { colspan: 4 },
                      { colspan: 3 },
                      { colspan: 4 },
                      { colspan: 1 },
                    ]}
                  >
                    <div>{t('indexName')}</div>
                    <div>{t('indexType')}</div>
                    <div>
                      {
                        <>
                          {t('desc')} - {t('optional')}
                        </>
                      }
                    </div>
                    <div></div>
                  </Grid>
                  <div style={{ marginTop: -30 }}>
                    {indexList.map((item, index) => {
                      return (
                        <Grid
                          gridDefinition={[
                            { colspan: 4 },
                            { colspan: 3 },
                            { colspan: 4 },
                            { colspan: 1 },
                          ]}
                        >
                          <FormField errorText={item.errText}>
                            <Input
                              placeholder={t('indexPlaceholder')}
                              disabled={useDefaultIndex}
                              onChange={({ detail }) => {
                                changeIndexName(detail.value, index);
                              }}
                              value={item.name}
                            />
                          </FormField>
                          <FormField>
                            <Select
                              disabled={useDefaultIndex || index < 3}
                              selectedOption={{
                                label: item.type,
                                value: item.type,
                              }}
                              options={indexTypeOption}
                              onChange={({ detail }: { detail: any }) =>
                                changeIndexType(
                                  detail.selectedOption.value,
                                  index,
                                )
                              }
                            ></Select>
                          </FormField>
                          <FormField>
                            <Input
                              placeholder={t('indexPlaceholderDesc')}
                              disabled={useDefaultIndex}
                              onChange={({ detail }) => {
                                changeIndexDesc(detail.value, index);
                              }}
                              value={item.desc}
                            />
                          </FormField>
                          {!useDefaultIndex && index > 2 && (
                            // <FormField >
                            <Link onFollow={() => removeIndex(index)}>
                              <img alt="banner" src={minus} width="35px" />
                            </Link>
                            // </FormField>
                          )}
                        </Grid>
                      );
                    })}
                    {!useDefaultIndex && (
                      <div style={{ marginTop: 20 }}>
                        <Link onFollow={() => addIndex()}>
                          <img alt="banner" src={plus} width="35px" />
                        </Link>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', paddingTop: 100 }}>
                  <div
                    style={{
                      marginTop: 135,
                      fontSize: 16,
                      color: '#5F6B7A',
                      margin: '0 auto',
                    }}
                  >
                    {t('indexLeft')}&nbsp;&nbsp;
                    <Link onFollow={() => addIndex()}>
                      <img alt="banner" src={plus} width="20px" />
                    </Link>
                    &nbsp;&nbsp; {t('indexRight')}
                  </div>
                </div>
              )}

              <div style={{ height: 20 }}></div>
            </SpaceBetween>
          </div>
          {/* <div className="create-chatbot-modal-foot">
              <div className="create-chatbot-modal-foot-content"> */}
              <div style={{width:"100%", marginBottom:20}}>
                <div style={{display:"block",marginLeft:"auto",width:"fit-content",marginRight: 50}}>
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
                  <Button
                    loading={loadingSave}
                    variant="primary"
                    onClick={() => {
                      createChatbot();
                    }}
                  >
                    {t('button.createChatbot')}
                  </Button>
                </SpaceBetween>
                </div>
                </div>
              {/* </div>
            </div> */}
        </RightModal>

        {/* <Modal
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
        </Modal> */}
      </ContentLayout>
    </CommonLayout>
  );
};

export default ChatbotManagement;
