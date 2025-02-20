import React, { useCallback, useEffect, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Box,
  Button,
  ButtonDropdown,
  CollectionPreferences,
  ContentLayout,
  Header,
  Modal,
  Pagination,
  SpaceBetween,
  StatusIndicator,
  Table,
  TableProps,
} from '@cloudscape-design/components';
import { LibraryListItem, LibraryListResponse } from 'src/types';
import { alertMsg, formatTime } from 'src/utils/utils';
import TableLink from 'src/comps/link/TableLink';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';
import AddLibrary from '../components/AddLibrary';

const parseDate = (item: LibraryListItem) => {
  return item.createTime ? new Date(item.createTime) : 0;
};

const Library: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<LibraryListItem[]>([]);
  const fetchData = useAxiosRequest();
  const [showDelete, setShowDelete] = useState(false);
  const { t } = useTranslation();
  const [loadingData, setLoadingData] = useState(false);
  const [allLibraryList, setAllLibraryList] = useState<LibraryListItem[]>([]);
  const [tableLibraryList, setTableLibraryList] = useState<LibraryListItem[]>(
    [],
  );
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [loadingDelete, setLoadingDelete] = useState(false);
  const [sortingColumn, setSortingColumn] = useState<
    TableProps.SortingColumn<LibraryListItem>
  >({
    sortingField: 'createTime',
  });
  const [isDescending, setIsDescending] = useState<boolean | undefined>(true);

  // ingest document
  const [showAddModal, setShowAddModal] = useState(false);
  const [isUpdate, setIsUpdate] = useState(false);

  const getLibraryList = async () => {
    setLoadingData(true);
    setSelectedItems([]);
    const params = {
      max_items: 9999,
      page_size: 9999,
    };
    try {
      const data = await fetchData({
        url: 'knowledge-base/executions',
        method: 'get',
        params,
      });
      const items: LibraryListResponse = data;
      const preSortItem = items.Items;
      preSortItem.sort((a, b) => {
        return Number(parseDate(b)) - Number(parseDate(a));
      });
      setAllLibraryList(preSortItem);
      setTableLibraryList(preSortItem.slice(0, pageSize));
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  };

  const removeLibrary = async () => {
    try {
      setLoadingDelete(true);
      const data = await fetchData({
        url: `knowledge-base/executions`,
        method: 'delete',
        data: { executionId: selectedItems.map((item) => item.executionId) },
      });
      setShowDelete(false);
      getLibraryList();
      alertMsg(data.Message, 'success');
      setLoadingDelete(false);
      setSelectedItems([]);
    } catch (error: unknown) {
      setLoadingDelete(false);
    }
  };

  useEffect(() => {
    getLibraryList();
  }, []);

  useEffect(() => {
    setTableLibraryList(
      allLibraryList.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
      ),
    );
  }, [currentPage, pageSize]);

  const renderStatus = (status: string) => {
    if (status === 'COMPLETED') {
      return <StatusIndicator type="success">{t('completed')}</StatusIndicator>;
    } else if (status === 'IN-PROGRESS') {
      return <StatusIndicator type="loading">{t('inProgress')}</StatusIndicator>;
    } else if (status === 'UPDATING') {
      return <StatusIndicator type="loading">{t('updating')}</StatusIndicator>;
    } else if (status === 'DELETING') {
      return <StatusIndicator type="loading">{t('deleting')}</StatusIndicator>;
    } else {
      return <StatusIndicator type="error">{t('failed')}</StatusIndicator>;
    }
  };

  const LinkComp = useCallback(
    (item: LibraryListItem) => (
      <TableLink
        url={`/library/detail/${item.executionId}`}
        name={item.executionId}
      />
    ),
    [],
  );

  return (
    <CommonLayout
      activeHref="/library"
      breadCrumbs={[
        {
          text: t('name'),
          href: '/',
        },
        {
          text: t('docLibrary'),
          href: '/library',
        },
      ]}
    >
      <ContentLayout>
        <div style={{marginTop: '25px'}} />
        <Table
          resizableColumns
          loading={loadingData}
          onSelectionChange={({ detail }) =>
            setSelectedItems(detail.selectedItems)
          }
          sortingDescending={isDescending}
          sortingColumn={sortingColumn}
          onSortingChange={({ detail }) => {
            const { sortingColumn, isDescending } = detail;
            const sortedItems = [...tableLibraryList].sort((a, b) => {
              setSortingColumn(sortingColumn);
              setIsDescending(isDescending);
              if (sortingColumn.sortingField === 'createTime') {
                return !isDescending
                  ? Number(parseDate(a)) - Number(parseDate(b))
                  : Number(parseDate(b)) - Number(parseDate(a));
              }
              if (sortingColumn.sortingField === 's3Prefix') {
                return !isDescending
                  ? a.s3Prefix.localeCompare(b.s3Prefix)
                  : b.s3Prefix.localeCompare(a.s3Prefix);
              }
              // if (sortingColumn.sortingField === 'indexType') {
              //   return !isDescending
              //     ? a.indexType.localeCompare(b.indexType)
              //     : b.indexType.localeCompare(a.indexType);
              // }
              if (sortingColumn.sortingField === 'chatbotId') {
                return !isDescending
                  ? a.chatbotId.localeCompare(b.chatbotId)
                  : b.chatbotId.localeCompare(a.chatbotId);
              }
              if (sortingColumn.sortingField === 'executionStatus') {
                return !isDescending
                  ? a.executionStatus.localeCompare(b.executionStatus)
                  : b.executionStatus.localeCompare(a.executionStatus);
              }
              return 0;
            });
            setTableLibraryList(sortedItems);
          }}
          selectedItems={selectedItems}
          ariaLabels={{
            allItemsSelectionLabel: ({ selectedItems }) =>
              `${selectedItems.length} ${
                selectedItems.length === 1 ? t('item') : t('items')
              } ${t('selected')}`,
          }}
          columnDefinitions={[
            {
              id: 'executionId',
              header: t('id'),
              cell: (item: LibraryListItem) => LinkComp(item),
              isRowHeader: true,
            },
            {
              id: 'chatbotId',
              header: t('chatbotName'),
              cell: (item: LibraryListItem) => item.chatbotId,
            },
            {
              id: 's3Prefix',
              header: t('docName'),
              sortingField: 's3Prefix',
              cell: (item: LibraryListItem) => {
                return item.s3Prefix.split('/').pop();
              },
            },
            // {
            //   width: 120,
            //   id: 'indexType',
            //   header: t('indexType'),
            //   sortingField: 'indexType',
            //   cell: (item: LibraryListItem) => item.indexType,
            // },
            {
              width: 150,
              id: 'executionStatus',
              header: t('status'),
              sortingField: 'executionStatus',
              cell: (item: LibraryListItem) =>
                renderStatus(item.executionStatus),
            },
            {
              width: 180,
              id: 'createTime',
              header: t('createTime'),
              sortingField: 'createTime',
              cell: (item: LibraryListItem) => formatTime(item.createTime),
            },
          ]}
          items={tableLibraryList}
          loadingText={t('loadingData')}
          selectionType="multi"
          trackBy="executionId"
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
              pagesCount={Math.ceil(allLibraryList.length / pageSize)}
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
                      getLibraryList();
                    }}
                  />
                  <ButtonDropdown
                    disabled={selectedItems.length === 0}
                    loading={loadingData}
                    onItemClick={({ detail }) => {
                      if (detail.id === 'update') {
                        setIsUpdate(true);
                        setShowAddModal(true);
                      }
                      if (detail.id === 'delete') {
                        setShowDelete(true);
                      }
                    }}
                    items={[
                      { text: t('button.update'), id: 'update', disabled: selectedItems.length !== 1 },
                      { text: t('button.delete'), id: 'delete' },
                    ]}
                  >
                    {t('button.action')}
                  </ButtonDropdown>
                  <Button
                    variant="primary"
                    onClick={() => {
                      setIsUpdate(false);
                      setShowAddModal(true);
                    }}
                  >
                    {t('button.createDoc')}
                  </Button>
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${allLibraryList.length})`
                  : `(${allLibraryList.length})`
              }
            >
              {t('docLibrary')}
            </Header>
          }
        />
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
                  loading={loadingDelete}
                  variant="primary"
                  onClick={() => {
                    removeLibrary();
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
                <li key={item.executionId}>{item.s3Prefix.split('/').pop()}</li>
              ))}
            </ul>
          </div>
        </Modal>
        <AddLibrary
          showAddModal={showAddModal}
          setShowAddModal={setShowAddModal}
          reloadLibrary={() => {
            setTimeout(() => {
              getLibraryList();
            }, 2000);
          }}
          selectedItem={isUpdate ? selectedItems[0] : undefined}
          isUpdate={isUpdate}
        />
      </ContentLayout>
    </CommonLayout>
  );
};

export default Library;
