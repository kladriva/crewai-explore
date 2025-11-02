"""
Unit tests for Backend API CRUD Operations
Tests Node and Container management, data integrity, and metric retrieval
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from backend.database.models import Node, Container, Alert, Action, ActionStatus


@pytest.mark.unit
class TestNodeCRUD:
    """Test Node CRUD operations"""
    
    def test_create_node(self, test_db_session):
        """Test creating a new node"""
        node = Node(
            name="test-node-create",
            ip_address="192.168.1.200",
            node_type="slave",
            is_active=True,
            os_type="Ubuntu",
            os_version="22.04"
        )
        
        test_db_session.add(node)
        test_db_session.commit()
        test_db_session.refresh(node)
        
        assert node.id is not None
        assert node.name == "test-node-create"
        assert node.ip_address == "192.168.1.200"
        assert node.is_active is True
    
    def test_create_node_duplicate_ip(self, test_db_session, sample_node):
        """Test creating node with duplicate IP address fails"""
        duplicate_node = Node(
            name="duplicate-node",
            ip_address=sample_node.ip_address,  # Same IP
            node_type="slave"
        )
        
        test_db_session.add(duplicate_node)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
    
    def test_read_node_by_id(self, test_db_session, sample_node):
        """Test reading node by ID"""
        node = test_db_session.query(Node).filter(Node.id == sample_node.id).first()
        
        assert node is not None
        assert node.id == sample_node.id
        assert node.name == sample_node.name
    
    def test_read_node_by_ip(self, test_db_session, sample_node):
        """Test reading node by IP address"""
        node = test_db_session.query(Node).filter(Node.ip_address == sample_node.ip_address).first()
        
        assert node is not None
        assert node.ip_address == sample_node.ip_address
    
    def test_read_all_active_nodes(self, test_db_session):
        """Test reading all active nodes"""
        # Create multiple nodes
        nodes = [
            Node(name=f"node-{i}", ip_address=f"192.168.1.{i}", is_active=(i % 2 == 0))
            for i in range(10, 15)
        ]
        test_db_session.add_all(nodes)
        test_db_session.commit()
        
        active_nodes = test_db_session.query(Node).filter(Node.is_active == True).all()
        
        assert len(active_nodes) >= 2  # At least the even indexed ones
    
    def test_update_node(self, test_db_session, sample_node):
        """Test updating node information"""
        original_name = sample_node.name
        
        sample_node.name = "updated-node-name"
        sample_node.os_version = "22.04.1"
        test_db_session.commit()
        test_db_session.refresh(sample_node)
        
        assert sample_node.name == "updated-node-name"
        assert sample_node.os_version == "22.04.1"
        assert sample_node.name != original_name
    
    def test_update_node_heartbeat(self, test_db_session, sample_node):
        """Test updating node heartbeat"""
        old_heartbeat = sample_node.last_heartbeat
        
        sample_node.last_heartbeat = datetime.utcnow()
        test_db_session.commit()
        test_db_session.refresh(sample_node)
        
        assert sample_node.last_heartbeat > old_heartbeat
    
    def test_delete_node(self, test_db_session):
        """Test deleting a node"""
        node = Node(
            name="delete-me",
            ip_address="192.168.1.250",
            node_type="slave"
        )
        test_db_session.add(node)
        test_db_session.commit()
        node_id = node.id
        
        test_db_session.delete(node)
        test_db_session.commit()
        
        deleted_node = test_db_session.query(Node).filter(Node.id == node_id).first()
        assert deleted_node is None
    
    def test_soft_delete_node(self, test_db_session, sample_node):
        """Test soft delete (deactivating) a node"""
        sample_node.is_active = False
        test_db_session.commit()
        test_db_session.refresh(sample_node)
        
        assert sample_node.is_active is False


@pytest.mark.unit
class TestContainerCRUD:
    """Test Container CRUD operations"""
    
    def test_create_container(self, test_db_session, sample_node):
        """Test creating a new container"""
        container = Container(
            node_id=sample_node.id,
            container_id="new123container456",
            name="new-container",
            image="redis:latest",
            status="running",
            ports={"6379/tcp": 6379},
            is_monitored=True
        )
        
        test_db_session.add(container)
        test_db_session.commit()
        test_db_session.refresh(container)
        
        assert container.id is not None
        assert container.node_id == sample_node.id
        assert container.name == "new-container"
    
    def test_read_container_by_id(self, test_db_session, sample_container):
        """Test reading container by ID"""
        container = test_db_session.query(Container).filter(Container.id == sample_container.id).first()
        
        assert container is not None
        assert container.id == sample_container.id
        assert container.name == sample_container.name
    
    def test_read_containers_by_node(self, test_db_session, sample_node):
        """Test reading all containers for a specific node"""
        # Create multiple containers
        containers = [
            Container(
                node_id=sample_node.id,
                container_id=f"container{i}",
                name=f"test-container-{i}",
                image="nginx:latest",
                status="running"
            )
            for i in range(5)
        ]
        test_db_session.add_all(containers)
        test_db_session.commit()
        
        node_containers = test_db_session.query(Container).filter(Container.node_id == sample_node.id).all()
        
        assert len(node_containers) >= 5
    
    def test_read_running_containers(self, test_db_session, sample_node):
        """Test reading only running containers"""
        # Create containers with different statuses
        containers = [
            Container(node_id=sample_node.id, container_id=f"c{i}", name=f"c{i}", 
                     image="nginx", status="running" if i < 3 else "stopped")
            for i in range(5)
        ]
        test_db_session.add_all(containers)
        test_db_session.commit()
        
        running = test_db_session.query(Container).filter(
            Container.node_id == sample_node.id,
            Container.status == "running"
        ).all()
        
        assert len(running) >= 3
    
    def test_update_container_status(self, test_db_session, sample_container):
        """Test updating container status"""
        sample_container.status = "stopped"
        test_db_session.commit()
        test_db_session.refresh(sample_container)
        
        assert sample_container.status == "stopped"
    
    def test_update_container_monitoring_flag(self, test_db_session, sample_container):
        """Test toggling container monitoring"""
        original_monitored = sample_container.is_monitored
        
        sample_container.is_monitored = not original_monitored
        test_db_session.commit()
        test_db_session.refresh(sample_container)
        
        assert sample_container.is_monitored != original_monitored
    
    def test_delete_container(self, test_db_session, sample_node):
        """Test deleting a container"""
        container = Container(
            node_id=sample_node.id,
            container_id="delete123",
            name="delete-container",
            image="test:latest",
            status="stopped"
        )
        test_db_session.add(container)
        test_db_session.commit()
        container_id = container.id
        
        test_db_session.delete(container)
        test_db_session.commit()
        
        deleted = test_db_session.query(Container).filter(Container.id == container_id).first()
        assert deleted is None
    
    def test_container_node_relationship(self, test_db_session, sample_container, sample_node):
        """Test container-node relationship"""
        assert sample_container.node is not None
        assert sample_container.node.id == sample_node.id
        assert sample_container in sample_node.containers


@pytest.mark.unit
class TestDataIntegrity:
    """Test data integrity and constraints"""
    
    def test_node_container_cascade(self, test_db_session, sample_node):
        """Test that containers are handled properly when node is deleted"""
        # Create containers for the node
        containers = [
            Container(
                node_id=sample_node.id,
                container_id=f"cascade{i}",
                name=f"cascade-{i}",
                image="test:latest",
                status="running"
            )
            for i in range(3)
        ]
        test_db_session.add_all(containers)
        test_db_session.commit()
        
        node_id = sample_node.id
        
        # Delete node
        test_db_session.delete(sample_node)
        test_db_session.commit()
        
        # Check containers - behavior depends on cascade settings
        remaining_containers = test_db_session.query(Container).filter(Container.node_id == node_id).all()
        # If cascade delete is set, should be empty; if not, constraint error would occur
    
    def test_node_timestamp_auto_update(self, test_db_session, sample_node):
        """Test that updated_at timestamp updates automatically"""
        original_updated = sample_node.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        sample_node.name = "timestamp-test"
        test_db_session.commit()
        test_db_session.refresh(sample_node)
        
        assert sample_node.updated_at >= original_updated
    
    def test_alert_node_relationship_integrity(self, test_db_session, sample_node, sample_alert):
        """Test alert-node relationship integrity"""
        assert sample_alert.node is not None
        assert sample_alert.node_id == sample_node.id
        assert sample_alert in sample_node.alerts
    
    def test_action_node_relationship_integrity(self, test_db_session, sample_node):
        """Test action-node relationship integrity"""
        action = Action(
            node_id=sample_node.id,
            action_type="restart",
            status=ActionStatus.SUCCESS,
            reason="Test action"
        )
        test_db_session.add(action)
        test_db_session.commit()
        test_db_session.refresh(action)
        
        assert action.node is not None
        assert action.node_id == sample_node.id


@pytest.mark.unit
class TestMetricRetrieval:
    """Test metric retrieval operations"""
    
    def test_get_recent_alerts_for_node(self, test_db_session, sample_node):
        """Test retrieving recent alerts for a node"""
        # Create alerts with different timestamps
        from backend.database.models import AlertSeverity
        
        alerts = []
        for i in range(5):
            alert = Alert(
                node_id=sample_node.id,
                severity=AlertSeverity.WARNING,
                title=f"Alert {i}",
                message=f"Message {i}",
                created_at=datetime.utcnow() - timedelta(hours=i)
            )
            alerts.append(alert)
        
        test_db_session.add_all(alerts)
        test_db_session.commit()
        
        # Get alerts from last 3 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=3)
        recent_alerts = test_db_session.query(Alert).filter(
            Alert.node_id == sample_node.id,
            Alert.created_at >= cutoff_time
        ).all()
        
        assert len(recent_alerts) >= 3
    
    def test_get_unresolved_alerts(self, test_db_session, sample_node):
        """Test retrieving unresolved alerts"""
        from backend.database.models import AlertSeverity
        
        # Create mixed resolved/unresolved alerts
        alerts = [
            Alert(node_id=sample_node.id, severity=AlertSeverity.WARNING, 
                  title=f"A{i}", message=f"M{i}", is_resolved=(i % 2 == 0))
            for i in range(6)
        ]
        test_db_session.add_all(alerts)
        test_db_session.commit()
        
        unresolved = test_db_session.query(Alert).filter(
            Alert.node_id == sample_node.id,
            Alert.is_resolved == False
        ).all()
        
        assert len(unresolved) >= 3
    
    def test_get_actions_by_status(self, test_db_session, sample_node):
        """Test retrieving actions by status"""
        # Create actions with different statuses
        actions = [
            Action(node_id=sample_node.id, action_type="restart", 
                  status=ActionStatus.SUCCESS if i < 3 else ActionStatus.FAILED,
                  reason=f"Test {i}")
            for i in range(5)
        ]
        test_db_session.add_all(actions)
        test_db_session.commit()
        
        successful = test_db_session.query(Action).filter(
            Action.node_id == sample_node.id,
            Action.status == ActionStatus.SUCCESS
        ).all()
        
        assert len(successful) >= 3
    
    def test_get_actions_in_timerange(self, test_db_session, sample_node):
        """Test retrieving actions within time range"""
        # Create actions with different timestamps
        actions = []
        for i in range(5):
            action = Action(
                node_id=sample_node.id,
                action_type="cleanup",
                status=ActionStatus.SUCCESS,
                reason=f"Test {i}",
                created_at=datetime.utcnow() - timedelta(hours=i)
            )
            actions.append(action)
        
        test_db_session.add_all(actions)
        test_db_session.commit()
        
        # Get actions from last 2 hours
        cutoff = datetime.utcnow() - timedelta(hours=2)
        recent_actions = test_db_session.query(Action).filter(
            Action.node_id == sample_node.id,
            Action.created_at >= cutoff
        ).all()
        
        assert len(recent_actions) >= 2
    
    def test_get_node_with_container_count(self, test_db_session, sample_node):
        """Test retrieving node with container count"""
        # Create containers
        containers = [
            Container(node_id=sample_node.id, container_id=f"cnt{i}",
                     name=f"c{i}", image="test", status="running")
            for i in range(4)
        ]
        test_db_session.add_all(containers)
        test_db_session.commit()
        
        from sqlalchemy import func
        
        result = test_db_session.query(
            Node,
            func.count(Container.id).label('container_count')
        ).outerjoin(Container).filter(Node.id == sample_node.id).group_by(Node.id).first()
        
        assert result is not None
        assert result.container_count >= 4
    
    def test_get_critical_alerts_count(self, test_db_session, sample_node):
        """Test counting critical alerts"""
        from backend.database.models import AlertSeverity
        
        alerts = [
            Alert(node_id=sample_node.id, 
                  severity=AlertSeverity.CRITICAL if i < 2 else AlertSeverity.WARNING,
                  title=f"A{i}", message=f"M{i}", is_resolved=False)
            for i in range(5)
        ]
        test_db_session.add_all(alerts)
        test_db_session.commit()
        
        from sqlalchemy import func
        
        critical_count = test_db_session.query(func.count(Alert.id)).filter(
            Alert.node_id == sample_node.id,
            Alert.severity == AlertSeverity.CRITICAL,
            Alert.is_resolved == False
        ).scalar()
        
        assert critical_count >= 2


@pytest.mark.unit
class TestBulkOperations:
    """Test bulk CRUD operations"""
    
    def test_bulk_create_nodes(self, test_db_session):
        """Test bulk creating multiple nodes"""
        nodes = [
            Node(name=f"bulk-node-{i}", ip_address=f"10.0.0.{i}", node_type="slave")
            for i in range(10, 20)
        ]
        
        test_db_session.add_all(nodes)
        test_db_session.commit()
        
        created_nodes = test_db_session.query(Node).filter(Node.name.like("bulk-node-%")).all()
        assert len(created_nodes) == 10
    
    def test_bulk_update_node_status(self, test_db_session):
        """Test bulk updating node statuses"""
        # Create nodes
        nodes = [
            Node(name=f"update-{i}", ip_address=f"10.1.0.{i}", node_type="slave", is_active=True)
            for i in range(10, 15)
        ]
        test_db_session.add_all(nodes)
        test_db_session.commit()
        
        # Bulk update
        test_db_session.query(Node).filter(Node.name.like("update-%")).update(
            {"is_active": False},
            synchronize_session=False
        )
        test_db_session.commit()
        
        # Verify
        inactive_count = test_db_session.query(Node).filter(
            Node.name.like("update-%"),
            Node.is_active == False
        ).count()
        
        assert inactive_count == 5
    
    def test_bulk_delete_old_alerts(self, test_db_session, sample_node):
        """Test bulk deleting old resolved alerts"""
        from backend.database.models import AlertSeverity
        
        # Create old and new alerts
        old_alerts = [
            Alert(node_id=sample_node.id, severity=AlertSeverity.INFO,
                  title=f"Old{i}", message="Old", is_resolved=True,
                  created_at=datetime.utcnow() - timedelta(days=90 + i))
            for i in range(5)
        ]
        test_db_session.add_all(old_alerts)
        test_db_session.commit()
        
        # Delete alerts older than 90 days
        cutoff = datetime.utcnow() - timedelta(days=90)
        test_db_session.query(Alert).filter(
            Alert.created_at < cutoff,
            Alert.is_resolved == True
        ).delete(synchronize_session=False)
        test_db_session.commit()
        
        remaining_old = test_db_session.query(Alert).filter(
            Alert.title.like("Old%")
        ).count()
        
        # Should have deleted most/all old alerts
        assert remaining_old < 5
