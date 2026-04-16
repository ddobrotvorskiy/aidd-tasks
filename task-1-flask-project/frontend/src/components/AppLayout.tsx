import { LogoutOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';
import { Button, Layout, Menu, Typography } from 'antd';
import React from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const { Header, Content } = Layout;

const AppLayout: React.FC = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Typography.Title level={4} style={{ color: '#fff', margin: 0, flex: 1 }}>
          Employee Directory
        </Typography.Title>
        <Menu theme="dark" mode="horizontal" selectable={false} style={{ flex: 2 }}>
          <Menu.Item key="employees" icon={<TeamOutlined />}>
            <Link to="/employees">Employees</Link>
          </Menu.Item>
          <Menu.Item key="profile" icon={<UserOutlined />}>
            <Link to="/profile">My Profile</Link>
          </Menu.Item>
        </Menu>
        <Button
          type="text"
          icon={<LogoutOutlined />}
          style={{ color: '#fff' }}
          onClick={handleLogout}
        >
          Logout
        </Button>
      </Header>
      <Content style={{ padding: '24px 48px' }}>
        <Outlet />
      </Content>
    </Layout>
  );
};

export default AppLayout;
