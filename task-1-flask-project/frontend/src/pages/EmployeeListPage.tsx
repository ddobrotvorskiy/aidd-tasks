import { Input, Pagination, Spin, Typography } from 'antd';
import React, { useState } from 'react';
import EmployeeCard from '../components/EmployeeCard';
import { useEmployees } from '../hooks/useEmployees';

const { Search } = Input;

const EmployeeListPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState<string | undefined>(undefined);
  const perPage = 20;

  const { data, isLoading, isError } = useEmployees(page, perPage, search);

  const handleSearch = (value: string) => {
    setSearch(value.trim() || undefined);
    setPage(1);
  };

  return (
    <div>
      <Typography.Title level={2}>Employees</Typography.Title>
      <Search
        placeholder="Search by name, phone, or email..."
        allowClear
        onSearch={handleSearch}
        style={{ maxWidth: 400, marginBottom: 24 }}
      />

      {isLoading && <Spin size="large" />}
      {isError && <Typography.Text type="danger">Failed to load employees.</Typography.Text>}

      {data && (
        <>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
            {data.items.map((emp) => (
              <EmployeeCard key={emp.id} employee={emp} />
            ))}
          </div>
          {data.total === 0 && (
            <Typography.Text type="secondary">No employees found.</Typography.Text>
          )}
          <Pagination
            current={page}
            total={data.total}
            pageSize={perPage}
            onChange={setPage}
            style={{ marginTop: 24 }}
            showSizeChanger={false}
          />
        </>
      )}
    </div>
  );
};

export default EmployeeListPage;
