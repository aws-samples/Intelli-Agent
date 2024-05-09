import React, { useCallback, useEffect, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Box,
  Button,
  ContentLayout,
  Header,
  Modal,
  SpaceBetween,
  StatusIndicator,
  Table,
  TextFilter,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import { LibraryListItem, LibraryListResponse } from 'src/types';
import { alertMsg, formatTime } from 'src/utils/utils';
import TableLink from 'src/comps/link/TableLink';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';

const parseDate = (item: LibraryListItem) => {
  return item.createTime ? new Date(item.createTime) : 0;
};

const Library: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<LibraryListItem[]>([]);
  const fetchData = useAxiosRequest();
  const [visible, setVisible] = useState(false);
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [loadingData, setLoadingData] = useState(false);
  const [libraryList, setLibraryList] = useState<LibraryListItem[]>([]);
  const [loadingDelete, setLoadingDelete] = useState(false);

  const getLibraryList = async () => {
    setLoadingData(true);
    const params = {
      size: 9999,
      total: 9999,
    };
    try {
      const data = await fetchData({
        url: 'etl/list-execution',
        method: 'get',
        params,
      });
      const items: LibraryListResponse = data;
      const preSortItem = items.Items;
      preSortItem.sort((a, b) => {
        return Number(parseDate(b)) - Number(parseDate(a));
      });
      setLibraryList(preSortItem);
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  };

  const removeLibrary = async () => {
    try {
      setLoadingDelete(true);
      const data = await fetchData({
        url: 'etl/delete-execution',
        method: 'post',
        data: { executionId: selectedItems.map((item) => item.executionId) },
      });
      setVisible(false);
      getLibraryList();
      alertMsg(data.message, 'success');
      setLoadingDelete(false);
      setSelectedItems([]);
    } catch (error: unknown) {
      setLoadingDelete(false);
    }
  };

  useEffect(() => {
    getLibraryList();
  }, []);

  const renderStatus = (status: string) => {
    if (status === 'COMPLETED') {
      return <StatusIndicator type="success">{t('completed')}</StatusIndicator>;
    } else if (status === 'IN-PROGRESS') {
      return (
        <StatusIndicator type="loading">{t('inProgress')}</StatusIndicator>
      );
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
        <Table
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
              id: 'executionId',
              header: t('id'),
              cell: (item: LibraryListItem) => LinkComp(item),
              sortingField: 'name',
              isRowHeader: true,
            },
            {
              id: 'bucket',
              header: t('bucket'),
              cell: (item: LibraryListItem) => item.s3Bucket,
              sortingField: 'alt',
            },
            {
              id: 'prefix',
              header: t('prefix'),
              cell: (item: LibraryListItem) => item.s3Prefix,
            },
            {
              width: 90,
              id: 'offline',
              header: t('offline'),
              cell: (item: LibraryListItem) =>
                item.offline === 'true' ? 'Yes' : 'No',
            },

            {
              width: 120,
              id: 'indexType',
              header: t('indexType'),
              cell: (item: LibraryListItem) => item.indexType,
            },
            {
              width: 150,
              id: 'status',
              header: t('status'),
              cell: (item: LibraryListItem) =>
                renderStatus(item.executionStatus),
            },
            {
              width: 180,
              id: 'createTime',
              header: t('createTime'),
              cell: (item: LibraryListItem) => formatTime(item.createTime),
            },
          ]}
          items={libraryList}
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
          filter={
            <TextFilter
              filteringPlaceholder={t('findResources')}
              filteringText=""
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
                  <Button
                    disabled={selectedItems.length <= 0}
                    onClick={() => {
                      setVisible(true);
                    }}
                  >
                    {t('button.delete')}
                  </Button>
                  <Button
                    variant="primary"
                    onClick={() => {
                      navigate('/library/add');
                    }}
                  >
                    {t('button.createDocLibrary')}
                  </Button>
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${libraryList.length})`
                  : `(${libraryList.length})`
              }
            >
              {t('docLibrary')}
            </Header>
          }
        />
        <Modal
          onDismiss={() => setVisible(false)}
          visible={visible}
          footer={
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="link"
                  onClick={() => {
                    setVisible(false);
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
          header="Delete"
        >
          <Box variant="h4">{t('deleteTips')}</Box>
          <div className="selected-items-list">
            <ul>
              {selectedItems.map((item) => (
                <li key={item.executionId}>{item.executionId}</li>
              ))}
            </ul>
          </div>
        </Modal>
      </ContentLayout>
    </CommonLayout>
  );
};

export default Library;
