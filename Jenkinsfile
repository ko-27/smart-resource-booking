pipeline {
    agent {
        label 'sscvk-agent'
    }
    triggers {
        githubPush()
    }
    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out source code from GitHub'
                checkout scm
            }
        }

        stage('Environment Check') {
            steps {
                echo 'Checking required tools'

                bat 'python --version'
                bat 'docker --version'
                bat 'wsl --version'
            }
        }

       stage('Automated Testing') {
         steps {
             echo 'Installing project dependencies'

             bat 'python -m pip install -r requirements.txt'

             echo 'Running automated tests'
  
             bat 'python -m pytest -v'
    	  }
	}

        stage('Ansible Deployment') {
            steps {
                echo 'Deploying application using Ansible'

                bat '''
                wsl bash -lc "cd /mnt/c/Users/sscvk/Documents/smart-resource-booking && ansible-playbook -i ansible/inventory.ini ansible/deploy.yml"
                '''
            }
        }

        stage('Deployment Verification') {
            steps {
                echo 'Verifying Docker deployment'

                bat 'docker ps --filter name=smart-resource-booking-container'
            }
        }
    }

    post {
        success {
            echo 'CI/CD PIPELINE COMPLETED SUCCESSFULLY'
        }

        failure {
            echo 'CI/CD PIPELINE FAILED - CHECK THE CONSOLE OUTPUT'
        }
    }
}