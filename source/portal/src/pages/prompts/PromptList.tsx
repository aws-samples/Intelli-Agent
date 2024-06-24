import React, { useEffect, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Autosuggest,
  Box,
  Button,
  ButtonDropdown,
  CollectionPreferences,
  ContentLayout,
  FormField,
  Header,
  Modal,
  Pagination,
  SpaceBetween,
  Table,
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
import { LLM_BOT_MODEL_LIST } from 'src/utils/const';

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
  const [currentPrompt, setCurrentPrompt] = useState('');
  const [modelOption, setModelOption] = useState<string>(LLM_BOT_MODEL_LIST[0]);

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
        url: 'prompt',
        method: 'get',
        params,
      });
      const items: PromptResponse = data;
      const preSortItem = items.Items.map((prompt) => {
        return {
          ...prompt,
          uuid: prompt.modelId + prompt.taskType,
        };
      });
      setAllPromptList(preSortItem);
      setTablePromptList(preSortItem.slice(0, pageSize));
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  };

  const getPromptById = async () => {
    setLoadingGet(true);
    try {
      const data: GetPromptResponse = await fetchData({
        url: `prompt/${selectedItems[0].modelId}/${selectedItems[0].taskType}`,
        method: 'get',
      });
      setLoadingGet(false);
      setCurrentPrompt(data.prompt.main);
      setShowEdit(true);
    } catch (error: unknown) {
      setLoadingGet(true);
    }
  };

  const deletePrompt = async () => {
    setLoadingSave(true);
    try {
      await fetchData({
        url: `prompt/${selectedItems[0].modelId}/${selectedItems[0].taskType}`,
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
    if (!modelOption.trim()) {
      setModelError(t('validation.requireModel'));
      return;
    }
    if (!currentPrompt.trim()) {
      setPromptError(t('validation.requirePrompt'));
      return;
    }
    setLoadingSave(true);
    const paramData = {
      model_id: modelOption,
      task_type: 'rag',
      prompt: {
        main: currentPrompt,
      },
    };
    try {
      const data = await fetchData({
        url: 'prompt',
        method: 'post',
        data: paramData,
      });
      const createRes: CreatePromptResponse = data;
      if (createRes.message === 'OK') {
        setShowCreate(false);
        setShowEdit(false);
        getPromptList();
      }
      setLoadingSave(false);
    } catch (error: unknown) {
      setLoadingSave(false);
    }
  };

  useEffect(() => {
    getPromptList();
  }, []);

  useEffect(() => {
    setTablePromptList(
      allPromptList.slice((currentPage - 1) * pageSize, currentPage * pageSize),
    );
  }, [currentPage, pageSize]);

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
              cell: (item: PromptItem) => item.modelId,
              isRowHeader: true,
            },
            {
              id: 'type',
              header: t('type'),
              cell: (item: PromptItem) => item.taskType,
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
                        getPromptById();
                      }
                    }}
                    items={[
                      { text: 'Edit', id: 'edit', disabled: false },
                      { text: 'Delete', id: 'delete', disabled: false },
                    ]}
                  >
                    Action
                  </ButtonDropdown>
                  <Button
                    variant="primary"
                    iconName="add-plus"
                    onClick={() => {
                      setCurrentPrompt('');
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
          onDismiss={() => setShowCreate(false)}
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
          <SpaceBetween direction="vertical" size="l">
            <FormField
              label={t('modelName')}
              stretch={true}
              errorText={modelError}
            >
              <Autosuggest
                disabled={showEdit}
                onChange={({ detail }) => {
                  setModelError('');
                  setModelOption(detail.value);
                }}
                value={modelOption}
                options={LLM_BOT_MODEL_LIST.map((item) => {
                  return {
                    label: item,
                    value: item,
                  };
                })}
                placeholder={t('validation.requireModel')}
                empty={t('noModelFound')}
              />
            </FormField>
            <FormField
              label={t('prompt')}
              stretch={true}
              errorText={promptError}
            >
              <Textarea
                placeholder={t('validation.requirePrompt')}
                value={currentPrompt}
                onChange={({ detail }) => {
                  setPromptError('');
                  setCurrentPrompt(detail.value);
                }}
              />
            </FormField>
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
                <li key={item.modelId + item.taskType}>
                  {item.modelId}({item.taskType})
                </li>
              ))}
            </ul>
          </div>
        </Modal>
      </ContentLayout>
    </CommonLayout>
  );
};

export default PromptList;
