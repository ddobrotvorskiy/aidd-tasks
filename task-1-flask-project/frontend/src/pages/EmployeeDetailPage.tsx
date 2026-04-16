import {
  ArrowLeftOutlined,
  MailOutlined,
  PhoneOutlined,
  TeamOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { Avatar, Button, Card, Descriptions, Spin, Typography } from 'antd';
import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useEmployee } from '../hooks/useEmployees';

const EmployeeDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const employeeId = Number(id);
  const navigate = useNavigate();

  const { data: employee, isLoading, isError } = useEmployee(employeeId);

  if (isLoading) return <Spin size="large" />;
  if (isError || !employee)
    return <Typography.Text type="danger">Employee not found.</Typography.Text>;

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(-1)}
        style={{ marginBottom: 16 }}
      >
        Back
      </Button>
      <Card>
        <div style={{ display: 'flex', gap: 32, alignItems: 'flex-start' }}>
          <Avatar
            size={120}
            src={employee.photo_url ?? undefined}
            style={{ backgroundColor: '#1677ff', flexShrink: 0 }}
          >
            {employee.full_name.charAt(0).toUpperCase()}
          </Avatar>
          <div style={{ flex: 1 }}>
            <Typography.Title level={3} style={{ marginTop: 0 }}>
              {employee.full_name}
            </Typography.Title>
            <Descriptions column={1} bordered size="small">
              {employee.job_title && (
                <Descriptions.Item label={<><TrophyOutlined /> Job Title</>}>
                  {employee.job_title}
                </Descriptions.Item>
              )}
              {employee.department && (
                <Descriptions.Item label={<><TeamOutlined /> Department</>}>
                  {employee.department}
                </Descriptions.Item>
              )}
              {employee.phone && (
                <Descriptions.Item label={<><PhoneOutlined /> Phone</>}>
                  {employee.phone}
                </Descriptions.Item>
              )}
              <Descriptions.Item label={<><MailOutlined /> Email</>}>
                <a href={`mailto:${employee.email}`}>{employee.email}</a>
              </Descriptions.Item>
            </Descriptions>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default EmployeeDetailPage;
