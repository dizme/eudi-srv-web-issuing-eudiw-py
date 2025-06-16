#!/bin/bash
#set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
LIGHTRED='\033[1;31m'
DARKGRAY='\033[1;30m'
NC='\033[0m' # No Color

IMAGEENV=image.env
DOCKER=$(which docker)
AWS=$(which aws)

# Public ECR
ECR_REPOSITORY=public.ecr.aws/dizme.io
AWS_REGION=us-east-1
AWS_PROFILE=default

if [ -f "$IMAGEENV" ]; then
    source "$IMAGEENV"
else
    echo -e "\n${RED}Missing file '$IMAGEENV'.${NC}"
    exit 1
fi

if [ -z ${PROJECT+x} ]; then
    echo -e "\n${RED}Missing env PROJECT${NC}"
    exit 1
fi

echo -en "Checking DOCKER: "
if ! $DOCKER help &> /dev/null
then
    echo -e "${RED}FAIL${NC}"
    echo -e "\n${RED}docker cli could not be found${NC}"
    exit
else
    echo -e "${GREEN}OK${NC}"
fi


echo
echo "Building project $PROJECT."
echo
PS3='Please enter staging environment: '
options=("TEST" "CL" "PR" "NO STAGING" "Quit")
VERSION_CURRENT=""
VERSION_NEWER=""
EDIT_IMAGE_ENV=1
SAVE_PROPERTY=1
select opt in "${options[@]}"
do
    echo
    case $opt in
        "TEST")
            FORCE_INSERT_VERSION=0
            if [ -z ${LAST_VERSION_TEST+x} ]; then
                echo -e "\n${RED}Property LAST_VERSION_TEST missing - ignore it${NC}"
                FORCE_INSERT_VERSION=1
                VERSION_PROPERTY_NAME="LAST_VERSION_TEST"
            else
                EDIT_IMAGE_ENV=1
                VERSION=$LAST_VERSION_TEST
                VERSION_CURRENT="LAST_VERSION_TEST=$LAST_VERSION_TEST"
                VERSION_NEWER="LAST_VERSION_TEST="
                echo -e "You choose TEST - last version saved was ${YELLOW}$LAST_VERSION_TEST${NC}"
            fi
            break
            ;;
        "CL")
            FORCE_INSERT_VERSION=0
            if [ -z ${LAST_VERSION_CL+x} ]; then
                echo -e "\n${RED}Property LAST_VERSION_CL missing - ignore it${NC}"
                FORCE_INSERT_VERSION=1
                VERSION_PROPERTY_NAME="LAST_VERSION_CL"
            else
                EDIT_IMAGE_ENV=1
                VERSION=$LAST_VERSION_CL
                VERSION_CURRENT="LAST_VERSION_CL=$LAST_VERSION_CL"
                VERSION_NEWER="LAST_VERSION_CL="
                echo -e "You choose CL - last version saved was ${YELLOW}$LAST_VERSION_CL${NC}"
            fi
            break
            ;;
        "PR")
            FORCE_INSERT_VERSION=0
            if [ -z ${LAST_VERSION_PR+x} ]; then
                echo -e "\n${RED}Property LAST_VERSION_PR missing - ignore it${NC}"
                FORCE_INSERT_VERSION=1
                VERSION_PROPERTY_NAME="LAST_VERSION_PR"
            else
                EDIT_IMAGE_ENV=1
                VERSION=$LAST_VERSION_PR
                VERSION_CURRENT="LAST_VERSION_PR=$LAST_VERSION_PR"
                VERSION_NEWER="LAST_VERSION_PR="
                echo -e "You choose PR - last version saved was ${YELLOW}$LAST_VERSION_PR${NC}"
            fi
            break
            ;;
        "NO STAGING")
            FORCE_INSERT_VERSION=1
            EDIT_IMAGE_ENV=0
            SAVE_PROPERTY=0
            break
            ;;
        "Quit")
            exit
            ;;
        *) echo -e "${RED}Invalid option $REPLY${NC}\n"
            sleep 1
            ;;
    esac
done

# just a new line
echo

while true; do
    if [ $FORCE_INSERT_VERSION == 1 ]; then
        STR="Insert a version number: "
    else
        STR="Confirm version '$VERSION' (press enter) or insert a new version number: "
    fi
    read -p "$STR" response

    responseLower=${response}  # tolower
    if [[ $responseLower =~ ^()$ ]]; then
        if [ $FORCE_INSERT_VERSION == 1 ]; then
            echo -e "\n${RED}Version number is mandatory.${NC}\n"
            continue
        fi
        break;
    fi

    VERSION=$response
    break
done

PUSH_ON_REPOSITORY_ECR=1

echo
echo "Choose Platform for $PROJECT."
echo
PS3='Please enter your choice: '
options=("linux/amd64" "linux/arm64" "Quit")
BUILD_PLATFORM=""
select opt in "${options[@]}"
do
    echo
    case $opt in
        "linux/amd64")
            BUILD_PLATFORM="linux/amd64"
            break
            ;;
        "linux/arm64")
            BUILD_PLATFORM="linux/arm64"
            break
            ;;
        "Quit")
            exit
            ;;
        *) echo -e "${RED}Invalid option $REPLY${NC}\n"
            sleep 1
            ;;
    esac
done

while true; do
    echo
    echo -e "Building and pushing image:"

    if [ $PUSH_ON_REPOSITORY_ECR == 1 ]; then
        echo -e "\tRepository ECR: ${YELLOW}$ECR_REPOSITORY${NC}"
    fi
    echo -e "\tProject: ${YELLOW}$PROJECT${NC}"
    echo -e "\tVersion: ${YELLOW}$VERSION${NC}"
    echo -e "\tPlatforms: ${YELLOW}$BUILD_PLATFORM${NC}"
    echo
    read -p "Do you want to proceed (Y/N)? " yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) echo -e "${LIGHTRED}Bye.${NC}"
                exit;;
        * ) echo -e "${LIGHTRED}Please answer yes or no.${NC}"
            sleep 1;;
    esac
done

URL_ECR=$ECR_REPOSITORY$PROJECT:$VERSION


if [ $PUSH_ON_REPOSITORY_ECR -eq 1 ]; then

    echo
    echo "Tag: $URL_ECR"
    echo "Building..."
    ### si potrebbe ottimizzare evitando il rebuild gestendo meglio il tag, ma essendo provvisorio l'ho lasciato cosi
#    $DOCKER image build --platform $BUILD_PLATFORM --build-arg CODEARTIFACT_AUTH_TOKEN --tag $URL_ECR -f api/Dockerfile .
    $DOCKER image build --platform $BUILD_PLATFORM --tag $URL_ECR -f Dockerfile .
    if [ $? != 0 ]; then
        echo -e "\n${RED}Some error occured during image building.${NC}"
        exit 1
    fi
    echo -e "\n${GREEN}Image builded${NC}"

    echo

    echo "Pushing to ECR..."

    echo -en "Checking AWS-CLI: "
    if ! aws help &> /dev/null
    then
        echo -e "${RED}FAIL${NC}"
        echo -e "\n${RED}aws cli not found${NC}"
        exit
    else
        echo -e "${GREEN}OK${NC}"
    fi

    echo -en "Checking AWS Profile dizme: "
    _C=`$AWS configure list-profiles | grep -w $AWS_PROFILE | wc -l`
    if [ $_C -eq 1 ]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        echo -e "\n${RED}missing profile dizme in aws credentials${NC}"
        exit 1
    fi

    $AWS ecr get-login-password --region $AWS_REGION --profile $AWS_PROFILE | docker login --username AWS --password-stdin $ECR_REPOSITORY
    $DOCKER image push $URL_ECR
    if [ $? != 0 ]; then
        echo -e "\n${RED}Some error occured during image pushing.${NC}"
        exit 1
    fi
    echo -e "\n${GREEN}Image pushed${NC}"
fi

# updating local image.env
echo -e "\n${YELLOW}Editing of local '$IMAGEENV' file.${NC}"

if [ $SAVE_PROPERTY == 1 ] && [ $FORCE_INSERT_VERSION == 1 ]; then
    NEW_PROPERTY="$VERSION_PROPERTY_NAME=$VERSION"
    while true; do
        echo
        read -p "Do you want insert property '$NEW_PROPERTY' in '$IMAGEENV' (Y/N)? " yn
        case $yn in
            [Yy]* )
                DO_SAVE_PROPERTY=1
                break;;
            [Nn]* )
                DO_SAVE_PROPERTY=0
                break;;
            * ) echo -e "${LIGHTRED}Please answer yes or no.${NC}"
                sleep 1;;
        esac
    done

    if [ $DO_SAVE_PROPERTY == 1 ]; then
        echo "$NEW_PROPERTY" >> "$IMAGEENV"
        echo -e "\n${GREEN}Added '$VERSION_PROPERTY_NAME' to local '$IMAGEENV' file.${NC}"
    else
        echo -e "\n${RED}Skip adding '$VERSION_PROPERTY_NAME' to local '$IMAGEENV' file.${NC}"
    fi
 else
    if [ $EDIT_IMAGE_ENV == 1 ]; then
        echo -e "\n${GREEN}Updating version in local '$IMAGEENV' file.${NC}"
        VERSION_NEWER=$VERSION_NEWER$VERSION
        sed -e s/"$VERSION_CURRENT"/"$VERSION_NEWER"/g "$IMAGEENV" > "$IMAGEENV.patch"
        mv "$IMAGEENV.patch" "$IMAGEENV"
    else
        echo -e "\n${RED}Skipping updating version in local '$IMAGEENV' file.${NC}"
    fi
fi

if [ $PUSH_ON_REPOSITORY_ECR -eq 1 ]; then
    echo -e "\n${GREEN}Image ${DARKGRAY}$URL_ECR${GREEN} builded and pushed correctly!${NC}"
fi
echo -e "\nBye\n\n"
