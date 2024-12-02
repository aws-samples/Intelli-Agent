import React, { useCallback, useEffect, useState } from 'react';
import CommonLayout from 'src/layout/CommonLayout';
import {
  Box,
  Button,
  CollectionPreferences,
  ContentLayout,
  Header,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
} from '@cloudscape-design/components';
import { SessionHistoryItem, SessionHistoryResponse } from 'src/types';
import { formatTime } from 'src/utils/utils';
import TableLink from 'src/comps/link/TableLink';
import useAxiosRequest from 'src/hooks/useAxiosRequest';
import { useTranslation } from 'react-i18next';

const parseDate = (item: SessionHistoryItem) => {
  return item.createTimestamp ? new Date(item.createTimestamp) : 0;
};

const SessionHistory: React.FC = () => {
  const [selectedItems, setSelectedItems] = useState<SessionHistoryItem[]>([]);
  const fetchData = useAxiosRequest();
  const { t } = useTranslation();
  const [loadingData, setLoadingData] = useState(false);
  const [allSessionList, setAllSessionList] = useState<SessionHistoryItem[]>(
    [],
  );
  const [tableSessionList, setTableSessionList] = useState<
    SessionHistoryItem[]
  >([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortingColumn, setSortingColumn] = useState<
    TableProps.SortingColumn<SessionHistoryItem>
  >({
    sortingField: 'createTimestamp',
  });
  const [isDescending, setIsDescending] = useState<boolean | undefined>(true);

  const getSessionList = async () => {
    setLoadingData(true);
    setSelectedItems([]);
    const params = {
      max_items: 9999,
      page_size: 9999,
    };
    try {
      const data = await fetchData({
        url: 'sessions',
        method: 'get',
        params,
      });
      const items: SessionHistoryResponse = data;
      const preSortItem = items.Items;
      preSortItem.sort((a, b) => {
        return Number(parseDate(b)) - Number(parseDate(a));
      });
      setAllSessionList(preSortItem);
      setTableSessionList(preSortItem.slice(0, pageSize));
      setLoadingData(false);
    } catch (error: unknown) {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    getSessionList();
  }, []);

  useEffect(() => {
    setTableSessionList(
      allSessionList.slice(
        (currentPage - 1) * pageSize,
        currentPage * pageSize,
      ),
    );
  }, [currentPage, pageSize]);

  const LinkComp = useCallback(
    (item: SessionHistoryItem) => (
      <TableLink
        url={`/session/detail/${item.sessionId}`}
        name={item.sessionId}
      />
    ),
    [],
  );

  return (
    <CommonLayout
      activeHref="/sessions"
      breadCrumbs={[
        {
          text: t('name'),
          href: '/',
        },
        {
          text: t('sessionHistory'),
          href: '/sessions',
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
          sortingDescending={isDescending}
          sortingColumn={sortingColumn}
          onSortingChange={({ detail }) => {
            const { sortingColumn, isDescending } = detail;
            const sortedItems = [...tableSessionList].sort((a, b) => {
              setSortingColumn(sortingColumn);
              setIsDescending(isDescending);
              if (sortingColumn.sortingField === 'createTimestamp') {
                return !isDescending
                  ? Number(parseDate(a)) - Number(parseDate(b))
                  : Number(parseDate(b)) - Number(parseDate(a));
              }
              return 0;
            });
            setTableSessionList(sortedItems);
          }}
          selectedItems={selectedItems}
          ariaLabels={{
            allItemsSelectionLabel: ({ selectedItems }) =>
              `${selectedItems.length} ${selectedItems.length === 1 ? t('item') : t('items')
              } ${t('selected')}`,
          }}
          columnDefinitions={[
            {
              id: 'sessionId',
              header: t('id'),
              cell: (item: SessionHistoryItem) => LinkComp(item),
              isRowHeader: true,
            },
            {
              id: 'latestQuestion',
              header: t('latestQuestion'),
              cell: (item: SessionHistoryItem) => item.latestQuestion,
            },
            {
              width: 180,
              id: 'createTimestamp',
              header: t('createTime'),
              sortingField: 'createTimestamp',
              cell: (item: SessionHistoryItem) =>
                formatTime(item.createTimestamp),
            },
          ]}
          items={tableSessionList}
          loadingText={t('loadingData')}
          trackBy="sessionId"
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
              pagesCount={Math.ceil(allSessionList.length / pageSize)}
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
                      getSessionList();
                    }}
                  />
                </SpaceBetween>
              }
              counter={
                selectedItems.length
                  ? `(${selectedItems.length}/${allSessionList.length})`
                  : `(${allSessionList.length})`
              }
            >
              {t('sessionHistory')}
            </Header>
          }
        />
      </ContentLayout>
    </CommonLayout>
  );
};

export default SessionHistory;
