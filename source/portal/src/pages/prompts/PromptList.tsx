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
  CreatePromptResponse,
  GetPromptResponse,
  PromptItem,
  PromptResponse,
} from 'src/types';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import { formatTime } from 'src/utils/utils';

const PromptList: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<PromptItem[]>([]);
  const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const [loadingData, setLoadingData] = useState(false);
  const [allPromptList, setAllPromptList] = useState<PromptItem[]>([]);
  const [tablePromptList, setTablePromptList] = useState<PromptItem[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [loadingSave, setLoadingSave] = useState(false);
  const [currentPrompt, setCurrentPrompt] = useState<GetPromptResponse>();
  const [modelList, setModelList] = useState<SelectProps.Option[]>([]);
  const [modelOption, setModelOption] = useState<SelectProps.Option | null>(
    null,
  );

  const [loadingGet, setLoadingGet] = useState(false);
  // validation
  const [modelError, setModelError] = useState('');
  const [promptError, setPromptError] = useState('');

  const [showDelete, setShowDelete] = useState(false);
  const getPromptList = async () => {
    setLoadingData(true);
    setSelectedItems([]);
    const params = {
      max_items: 9999,
      page_size: 9999,
    };
    try {
      const data = await fetchData({
        url: 'prompt-management/prompts',
        method: 'get',
        params,
      });
      const items: PromptResponse = data;
      const preSortItem = items.Items.map((prompt) => {
        return {
          ...prompt,
          uuid: prompt.SortKey,
        };
      });
      setAllPromptList(preSortItem);
      setTablePromptList(preSortItem.slice(0, pageSize));
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  };

  const getModalList = async (type: 'create' | 'edit') => {
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
      const data: GetPromptResponse = await fetchData({
        url: requestUrl,
        method: 'get',
      });
      setLoadingGet(false);
      setCurrentPrompt(data);
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
      getPromptList();
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
        data: currentPrompt,
      });
      const createRes: CreatePromptResponse = data;
      if (createRes.Message === 'OK') {
        setShowCreate(false);
        setShowEdit(false);
        getPromptList();
      }
      setLoadingSave(false);
    } catch (error: unknown) {
      setLoadingSave(false);
    }
  };

  const handlePromptChange = (key: string, subKey: string, value: string) => {
    setCurrentPrompt((prevData: any) => ({
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
    getPromptList();
  }, []);

  useEffect(() => {
    setTablePromptList(
      allPromptList.slice((currentPage - 1) * pageSize, currentPage * pageSize),
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
              cell: (item: PromptItem) => item.ModelId,
              isRowHeader: true,
            },
            {
              id: 'updateBy',
              header: t('updateBy'),
              cell: (item: PromptItem) => item.LastModifiedBy,
            },
            {
              id: 'updateTime',
              header: t('updateTime'),
              cell: (item: PromptItem) =>
                formatTime(parseInt(item.LastModifiedTime) * 1000),
            },
          ]}
          items={tablePromptList}
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
              pagesCount={Math.ceil(allPromptList.length / pageSize)}
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
                      getPromptList();
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
                      getModalList('create');
                      setShowCreate(true);
                    }}
                  >
                    {t('button.createPrompt')}
                  </Button>
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${allPromptList.length})`
                  : `(${allPromptList.length})`
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
              errorText={promptError}
            >
              {loadingGet ? (
                <Spinner />
              ) : (
                <Tabs
                  tabs={
                    currentPrompt?.Prompt
                      ? Object.keys(currentPrompt?.Prompt).map((key) => ({
                          label: key,
                          id: key,
                          content: (
                            <>
                              {Object.keys(currentPrompt?.Prompt[key]).map(
                                (subKey) => (
                                  <FormField key={subKey} label={subKey}>
                                    <Textarea
                                      rows={5}
                                      placeholder={t(
                                        'validation.requirePrompt',
                                      )}
                                      value={currentPrompt.Prompt[key][subKey]}
                                      onChange={({ detail }) => {
                                        setPromptError('');
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

export default PromptList;
